"""
Flask sample app for static analysis testing.

Contains:
  - One CLEARLY VULNERABLE POST route (POST /projects/<project_id>/archive)
    → no ownership check, directly archives any project by ID.
  - One CLEARLY SAFE DELETE route (DELETE /projects/<project_id>)
    → checks current_user.id == project.owner_id before deletion.
  - One SAFE PUT route (PUT /projects/<project_id>)
    → uses filter_by with user_id=current_user.id.
  - One VULNERABLE PATCH route (PATCH /users/<user_id>/role)
    → no ownership check, any authenticated user can change another's role.
  - One GET route that should be EXCLUDED entirely (GET is not state-changing).
"""

from flask import Flask, request, abort, jsonify, g, session

app = Flask(__name__)


# ── Fake models / DB helpers (for tree-sitter to parse) ───────────────────

class FakeQuery:
    @staticmethod
    def get(pk):
        return {"id": pk, "owner_id": 1, "name": "test", "archived": False}

    @staticmethod
    def filter_by(**kwargs):
        return FakeQuery()

    def first(self):
        return {"id": 1, "owner_id": 1}

    def update(self, data):
        pass

class Project:
    query = FakeQuery()

class User:
    query = FakeQuery()

class db:
    class session:
        @staticmethod
        def commit():
            pass
        @staticmethod
        def delete(obj):
            pass
        @staticmethod
        def add(obj):
            pass

class current_user:
    id = 1


# ── GET route: must NOT appear in results (not state-changing) ────────────

@app.route('/projects', methods=['GET'])
def list_projects():
    """List all projects — this is a read-only route, not BOLA-relevant."""
    projects = Project.query.filter_by()
    return jsonify([])


# ── VULNERABLE: POST /projects/<project_id>/archive ──────────────────────
#    No ownership check.  Any authenticated user can archive any project.

@app.post('/projects/<int:project_id>/archive')
def archive_project(project_id):
    """Archive a project — VULNERABLE: no ownership check."""
    project = Project.query.get(project_id)
    if project is None:
        abort(404)
    project.archived = True
    db.session.commit()
    return jsonify({"status": "archived"})


# ── SAFE: DELETE /projects/<project_id> ──────────────────────────────────
#    Explicitly checks current_user.id against project.owner_id.

@app.delete('/projects/<int:project_id>')
def delete_project(project_id):
    """Delete a project — SAFE: has ownership check."""
    project = Project.query.get(project_id)
    if project is None:
        abort(404)
    if current_user.id != project.owner_id:
        abort(403)
    db.session.delete(project)
    db.session.commit()
    return jsonify({"status": "deleted"})


# ── SAFE: PUT /projects/<project_id> ─────────────────────────────────────
#    Uses filter_by(user_id=current_user.id).

@app.route('/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Update a project — SAFE: ownership enforced via filter_by."""
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if project is None:
        abort(404)
    data = request.json
    project.update(data)
    db.session.commit()
    return jsonify({"status": "updated"})


# ── VULNERABLE: PATCH /users/<user_id>/role ──────────────────────────────
#    No ownership check — any user can change any other user's role.

@app.patch('/users/<int:user_id>/role')
def change_user_role(user_id):
    """Change a user's role — VULNERABLE: no ownership check."""
    user = User.query.get(user_id)
    if user is None:
        abort(404)
    new_role = request.json.get("role_id")
    user.update({"role": new_role})
    db.session.commit()
    return jsonify({"status": "role_changed"})
