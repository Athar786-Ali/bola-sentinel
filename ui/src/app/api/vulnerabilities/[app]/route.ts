import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ app: string }> }
) {
  try {
    const { app } = await params;
    const rootDir = path.join(process.cwd(), '..');
    const appDir = path.join(rootDir, 'results', 'benchmark_runs', app);
    const gtDir = path.join(rootDir, 'datasets', 'ground_truth');

    const safeParse = (filePath: string) => {
      try {
        if (fs.existsSync(filePath)) {
          return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
        }
      } catch {
        // ignore
      }
      return null;
    };

    const staticData = safeParse(path.join(appDir, 'static_analysis_results.json')) || [];
    const llmData = safeParse(path.join(appDir, 'llm_classified_results.json')) || [];
    const verifiedData = safeParse(path.join(appDir, 'final_verified_results.json')) || [];
    const gtData = safeParse(path.join(gtDir, `${app}.json`)) || {};

    const gtArray = Array.isArray(gtData) ? gtData : (gtData.routes || []);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const routesMap = new Map<string, any>();

    for (const gt of gtArray) {
      if (gt.route_id) {
        routesMap.set(gt.route_id, {
          route_id: gt.route_id,
          http_method: gt.http_method,
          endpoint: gt.endpoint,
          ground_truth: gt.actually_vulnerable,
        });
      }
    }

    for (const st of staticData) {
      if (st.route_id) {
        const existing = routesMap.get(st.route_id) || { route_id: st.route_id };
        routesMap.set(st.route_id, {
          ...existing,
          http_method: st.http_method || existing.http_method,
          endpoint: st.route_path || existing.endpoint,
          static_flagged: true,
        });
      }
    }

    for (const llm of llmData) {
      if (llm.route_id) {
        const existing = routesMap.get(llm.route_id) || { route_id: llm.route_id };
        routesMap.set(llm.route_id, {
          ...existing,
          llm_flagged: llm.is_vulnerable,
          llm_confidence: llm.confidence || 0,
          llm_explanation: llm.explanation || '',
        });
      }
    }

    for (const v of verifiedData) {
      if (v.route_id) {
        const existing = routesMap.get(v.route_id) || { route_id: v.route_id };
        routesMap.set(v.route_id, {
          ...existing,
          dynamically_verified: v.dynamically_verified,
          final_verdict: v.final_verdict || 'not_evaluated',
        });
      }
    }

    const result = Array.from(routesMap.values()).map((r) => {
      let risk_level = 'low';
      if (r.ground_truth && r.dynamically_verified) {
        risk_level = 'high';
      } else if (r.llm_flagged) {
        risk_level = 'medium';
      }

      return {
        route_id: r.route_id,
        http_method: r.http_method || 'UNKNOWN',
        endpoint: r.endpoint || 'unknown',
        static_flagged: r.static_flagged || false,
        llm_flagged: r.llm_flagged || false,
        llm_confidence: r.llm_confidence || 0,
        llm_explanation: r.llm_explanation || '',
        dynamically_verified: r.dynamically_verified || false,
        final_verdict: r.final_verdict || 'not_evaluated',
        ground_truth: r.ground_truth !== undefined ? r.ground_truth : null,
        risk_level,
      };
    });

    return NextResponse.json(result);
  } catch (error) {
    console.error('Error reading vulnerabilities:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
