/**
 * Express sample app for static analysis testing.
 *
 * Contains:
 *   - One CLEARLY VULNERABLE POST route (POST /orders/:orderId/cancel)
 *     → no ownership check, directly cancels any order by ID.
 *   - One CLEARLY SAFE DELETE route (DELETE /orders/:orderId)
 *     → checks req.user.id against order.userId before deletion.
 *   - One SAFE PUT route (PUT /orders/:orderId)
 *     → uses findOne with userId filter.
 *   - One VULNERABLE PATCH route (PATCH /users/:userId/email)
 *     → no ownership check, any user can change another's email.
 *   - One GET route that should be EXCLUDED (not state-changing).
 */

const express = require('express');
const router = express.Router();

// Fake model helpers
const Order = {
  findByPk: async (id) => ({ id, userId: 'user_001', status: 'active' }),
  findOne: async (query) => ({ id: 1, userId: 'user_001', status: 'active' }),
};

const User = {
  findByPk: async (id) => ({ id, email: 'old@example.com' }),
};


// ── GET route: must NOT appear in results (not state-changing) ──────────

router.get('/orders', async (req, res) => {
  const orders = await Order.findAll();
  res.json(orders);
});


// ── VULNERABLE: POST /orders/:orderId/cancel ────────────────────────────
//    No ownership check.  Any authenticated user can cancel any order.

router.post('/orders/:orderId/cancel', async (req, res) => {
  const order = await Order.findByPk(req.params.orderId);
  if (!order) {
    return res.status(404).json({ error: 'Not found' });
  }
  await order.update({ status: 'cancelled' });
  res.json({ status: 'cancelled' });
});


// ── SAFE: DELETE /orders/:orderId ───────────────────────────────────────
//    Explicitly checks req.user.id against order.userId.

router.delete('/orders/:orderId', async (req, res) => {
  const order = await Order.findByPk(req.params.orderId);
  if (!order) {
    return res.status(404).json({ error: 'Not found' });
  }
  if (req.user.id !== order.userId) {
    return res.status(403).json({ error: 'Forbidden' });
  }
  await order.destroy();
  res.json({ status: 'deleted' });
});


// ── SAFE: PUT /orders/:orderId ──────────────────────────────────────────
//    Uses findOne with userId filter from req.user.

router.put('/orders/:orderId', async (req, res) => {
  const order = await Order.findOne({
    where: { id: req.params.orderId, userId: req.user.id }
  });
  if (!order) {
    return res.status(404).json({ error: 'Not found' });
  }
  await order.update(req.body);
  res.json({ status: 'updated' });
});


// ── VULNERABLE: PATCH /users/:userId/email ──────────────────────────────
//    No ownership check — any authenticated user can change another's email.

router.patch('/users/:userId/email', async (req, res) => {
  const user = await User.findByPk(req.params.userId);
  if (!user) {
    return res.status(404).json({ error: 'Not found' });
  }
  await user.update({ email: req.body.email });
  res.json({ status: 'email_updated' });
});

module.exports = router;
