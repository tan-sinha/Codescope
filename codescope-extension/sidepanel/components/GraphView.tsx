import { useEffect, useRef, useState } from 'react';
import { useAppContext } from '../state/AppContext';
import { useApi } from '../hooks/useApi';
import type { GraphData, GraphType } from '../state/types';

// D3 is loaded dynamically to keep the bundle lean for simpler views.
// Install: npm i d3 @types/d3
async function renderGraph(
  svg: SVGSVGElement,
  data: GraphData,
  width: number,
  height: number
) {
  const d3 = await import('d3');

  const el = d3.select(svg);
  el.selectAll('*').remove();

  const nodeById = new Map(data.nodes.map((n) => [n.id, n]));

  const links = data.edges
    .filter((e) => nodeById.has(e.from) && nodeById.has(e.to))
    .map((e) => ({ source: e.from, target: e.to, type: e.type }));

  const nodes = data.nodes.map((n) => ({ ...n }));

  const color = d3.scaleOrdinal<string>()
    .domain(['function', 'method', 'class', 'source', 'external'])
    .range(['#4f9cf9', '#9c6ade', '#50c8a0', '#f0a030', '#888']);

  const sim = d3.forceSimulation(nodes as d3.SimulationNodeDatum[])
    .force('link', d3.forceLink(links).id((d: d3.SimulationNodeDatum) => (d as { id: string }).id).distance(80))
    .force('charge', d3.forceManyBody().strength(-200))
    .force('center', d3.forceCenter(width / 2, height / 2));

  const g = el.append('g');

  el.call(
    d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 4])
      .on('zoom', (event) => g.attr('transform', event.transform))
  );

  const link = g.append('g')
    .selectAll('line')
    .data(links)
    .join('line')
    .attr('stroke', '#ccc')
    .attr('stroke-width', 1.5)
    .attr('marker-end', 'url(#arrow)');

  el.append('defs').append('marker')
    .attr('id', 'arrow')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 18)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#ccc');

  const node = g.append('g')
    .selectAll('g')
    .data(nodes)
    .join('g')
    .call(
      d3.drag<SVGGElement, typeof nodes[0]>()
        .on('start', (event, d) => {
          if (!event.active) sim.alphaTarget(0.3).restart();
          (d as d3.SimulationNodeDatum).fx = (d as d3.SimulationNodeDatum).x;
          (d as d3.SimulationNodeDatum).fy = (d as d3.SimulationNodeDatum).y;
        })
        .on('drag', (event, d) => {
          (d as d3.SimulationNodeDatum).fx = event.x;
          (d as d3.SimulationNodeDatum).fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) sim.alphaTarget(0);
          (d as d3.SimulationNodeDatum).fx = null;
          (d as d3.SimulationNodeDatum).fy = null;
        })
    );

  node.append('circle')
    .attr('r', 8)
    .attr('fill', (d) => color(d.type));

  node.append('text')
    .attr('dx', 12)
    .attr('dy', 4)
    .attr('font-size', 11)
    .text((d) => d.id.split('/').pop() ?? d.id);

  node.append('title').text((d) => `${d.id}\n${d.file ?? 'external'}`);

  sim.on('tick', () => {
    link
      .attr('x1', (d) => (d.source as d3.SimulationNodeDatum).x ?? 0)
      .attr('y1', (d) => (d.source as d3.SimulationNodeDatum).y ?? 0)
      .attr('x2', (d) => (d.target as d3.SimulationNodeDatum).x ?? 0)
      .attr('y2', (d) => (d.target as d3.SimulationNodeDatum).y ?? 0);

    node.attr('transform', (d) =>
      `translate(${(d as d3.SimulationNodeDatum).x ?? 0},${(d as d3.SimulationNodeDatum).y ?? 0})`
    );
  });
}

export function GraphView() {
  const { owner, repo } = useAppContext();
  const { get, loading, error } = useApi();
  const svgRef = useRef<SVGSVGElement>(null);

  const [graphType, setGraphType] = useState<GraphType>('calls');
  const [root, setRoot] = useState('');
  const [depth, setDepth] = useState(3);
  const [graph, setGraph] = useState<GraphData | null>(null);

  useEffect(() => {
    if (!graph || !svgRef.current) return;
    const { width, height } = svgRef.current.getBoundingClientRect();
    renderGraph(svgRef.current, graph, width || 600, height || 400);
  }, [graph]);

  async function fetchGraph() {
    if (!owner || !repo) return;
    const params =
      graphType === 'calls'
        ? `?type=calls&root=${encodeURIComponent(root)}&depth=${depth}`
        : '?type=imports';
    const data = await get<GraphData>(`/graph/${owner}/${repo}${params}`);
    if (data) setGraph(data);
  }

  if (!owner || !repo) {
    return <p className="graph-view__hint">Navigate to a GitHub repository to view graphs.</p>;
  }

  return (
    <div className="graph-view">
      <div className="graph-view__controls">
        <select
          value={graphType}
          onChange={(e) => setGraphType(e.target.value as GraphType)}
        >
          <option value="calls">Call graph</option>
          <option value="imports">Import graph</option>
        </select>

        {graphType === 'calls' && (
          <>
            <input
              type="text"
              placeholder="Root function (e.g. Flask.route)"
              value={root}
              onChange={(e) => setRoot(e.target.value)}
            />
            <input
              type="number"
              min={1}
              max={10}
              value={depth}
              onChange={(e) => setDepth(Number(e.target.value))}
              style={{ width: 56 }}
            />
          </>
        )}

        <button onClick={fetchGraph} disabled={loading || (graphType === 'calls' && !root)}>
          {loading ? '…' : 'Load'}
        </button>
      </div>

      {error && <p className="graph-view__error">{error}</p>}

      {graph && (
        <p className="graph-view__stats">
          {graph.nodes.length} nodes · {graph.edges.length} edges
        </p>
      )}

      <svg
        ref={svgRef}
        className="graph-view__svg"
        width="100%"
        height="420"
      />
    </div>
  );
}
