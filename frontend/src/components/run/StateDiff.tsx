import React, { useMemo } from "react";

type Json = unknown;

function flatten(value: Json, path = "", out: Map<string, string> = new Map()): Map<string, string> {
  if (value !== null && typeof value === "object") {
    const entries = Array.isArray(value) ? value.map((v, i) => [String(i), v] as const) : Object.entries(value as Record<string, Json>);
    if (!entries.length) out.set(path || "(root)", Array.isArray(value) ? "[]" : "{}");
    for (const [k, v] of entries) flatten(v, path ? `${path}.${k}` : k, out);
  } else {
    out.set(path || "(root)", JSON.stringify(value));
  }
  return out;
}

/** Path-level diff of the PRE and POST environment snapshots (what the verdict actually reads). */
export const StateDiff: React.FC<{ pre: Json; post: Json }> = ({ pre, post }) => {
  const rows = useMemo(() => {
    const a = flatten(pre);
    const b = flatten(post);
    const keys = Array.from(new Set([...a.keys(), ...b.keys()])).sort();
    return keys
      .filter((k) => a.get(k) !== b.get(k))
      .map((k) => ({ path: k, before: a.get(k), after: b.get(k), kind: !a.has(k) ? "added" : !b.has(k) ? "removed" : "changed" }));
  }, [pre, post]);

  return (
    <div className="space-y-3">
      {rows.length === 0 ? (
        <p className="text-xs text-ink-2">PRE and POST snapshots are identical: the run changed no environment state.</p>
      ) : (
        <div className="overflow-x-auto rounded-md border border-line">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-surface-muted text-ink-2 font-sans">
              <tr>
                <th scope="col" className="px-2.5 py-1.5 font-medium">Change</th>
                <th scope="col" className="px-2.5 py-1.5 font-medium">Path</th>
                <th scope="col" className="px-2.5 py-1.5 font-medium">Before</th>
                <th scope="col" className="px-2.5 py-1.5 font-medium">After</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.map((r) => (
                <tr key={r.path}>
                  <td className="px-2.5 py-1.5 font-sans">
                    <span className={r.kind === "removed" ? "text-vuln" : r.kind === "added" ? "text-term" : "text-warn-ink"}>
                      {r.kind === "removed" ? "− removed" : r.kind === "added" ? "+ added" : "~ changed"}
                    </span>
                  </td>
                  <td className="px-2.5 py-1.5 text-ink whitespace-nowrap">{r.path}</td>
                  <td className="px-2.5 py-1.5 text-ink-2 max-w-[28ch] truncate" title={r.before}>
                    {r.before ?? "none"}
                  </td>
                  <td className="px-2.5 py-1.5 text-ink max-w-[28ch] truncate" title={r.after}>
                    {r.after ?? "none"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <details className="group">
        <summary className="cursor-pointer text-xs text-ink-2 hover:text-ink">Raw PRE and POST snapshots</summary>
        <div className="mt-2 grid gap-2 md:grid-cols-2">
          {(["PRE", "POST"] as const).map((label) => (
            <pre key={label} className="max-h-80 overflow-auto rounded-md border border-line bg-surface-muted p-2.5 text-[11px] leading-relaxed text-term">
              <span className="block font-sans text-ink-3 mb-1">{label}</span>
              {JSON.stringify(label === "PRE" ? pre : post, null, 2)}
            </pre>
          ))}
        </div>
      </details>
    </div>
  );
};
