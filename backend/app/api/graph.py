"""Grafo de dependências entre os componentes do catálogo.

As dependências chegam do `project-info.yml` como nomes soltos
(`spec.dependencies[].component`) e é assim que o crawler as grava: uma string,
sem chave estrangeira para o alvo. Resolver esses nomes contra o catálogo é o
trabalho deste módulo — junto com o que a resolução revela e que hoje ninguém
vê: alvos declarados que não existem no catálogo e ciclos de dependência.
"""

from collections import deque
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _component_node(c: Any) -> Dict[str, Any]:
    """Nó de um componente que existe no catálogo."""
    return {
        "id": f"c{c.id}",
        "component_id": c.id,
        "name": c.name,
        "kind": c.kind,
        "type": c.type,
        "lifecycle": c.lifecycle,
        "owner": c.owner,
        "domain": c.domain,
        "solution": c.solution,
        "resolved": True,
        "in_scope": True,
        "is_root": False,
        "is_external": False,
    }


def _unresolved_node(node_id: str, name: str, is_external: bool = False) -> Dict[str, Any]:
    """Nó de uma dependência declarada que não casa com nenhum componente.

    Pode ser um serviço externo legítimo (uma API de terceiro ou projeto externo) ou um nome
    errado no manifesto. O grafo não tem como distinguir os dois casos no nome solto,
    mas se for marcado como external=True ele fica identificado.
    """
    return {
        "id": node_id,
        "component_id": None,
        "name": name,
        "kind": None,
        "type": None,
        "lifecycle": None,
        "owner": None,
        "domain": None,
        "solution": None,
        "resolved": False,
        "in_scope": True,
        "is_root": False,
        "is_external": is_external,
    }


def _canonical_cycle(cycle: List[str]) -> Tuple[str, ...]:
    """Rotaciona o ciclo para começar sempre no mesmo nó.

    O mesmo ciclo é encontrado por caminhos diferentes dependendo de onde a
    busca começou; a rotação canônica é o que permite deduplicar.
    """
    pivot = cycle.index(min(cycle))
    return tuple(cycle[pivot:] + cycle[:pivot])


def _find_cycles(adjacency: Dict[str, List[str]]) -> List[List[str]]:
    """Ciclos de dependência do grafo dirigido.

    Busca em profundidade marcando os nós do caminho atual: toda aresta que
    aponta de volta para o caminho fecha um ciclo. Não enumera *todos* os
    ciclos simples de um grafo denso, mas sinaliza cada um dos que existem —
    que é o que a tela precisa mostrar.
    """
    cycles: List[List[str]] = []
    seen: Set[Tuple[str, ...]] = set()
    state: Dict[str, int] = {}  # 0/ausente: não visitado, 1: no caminho, 2: fechado
    path: List[str] = []

    def visit(node: str) -> None:
        state[node] = 1
        path.append(node)
        for nxt in adjacency.get(node, []):
            if state.get(nxt, 0) == 1:
                signature = _canonical_cycle(path[path.index(nxt):])
                if signature not in seen:
                    seen.add(signature)
                    cycles.append(list(signature))
            elif state.get(nxt, 0) == 0:
                visit(nxt)
        path.pop()
        state[node] = 2

    for node in sorted(adjacency):
        if state.get(node, 0) == 0:
            visit(node)
    return cycles


def _neighbourhood(origin: str, undirected: Dict[str, Set[str]], depth: int) -> Set[str]:
    """Nós alcançáveis a partir de `origin` em até `depth` saltos.

    A travessia ignora a direção das arestas de propósito: quem eu consumo e
    quem me consome são a mesma pergunta na tela de um projeto.
    """
    reached = {origin}
    frontier = deque([(origin, 0)])
    while frontier:
        node, distance = frontier.popleft()
        if distance >= depth:
            continue
        for neighbour in undirected.get(node, ()):
            if neighbour not in reached:
                reached.add(neighbour)
                frontier.append((neighbour, distance + 1))
    return reached


def build_graph(
    components: Iterable[Any],
    *,
    root_id: Optional[int] = None,
    depth: int = 1,
    domain: Optional[str] = None,
    solution: Optional[str] = None,
    include_isolated: bool = False,
) -> Optional[Dict[str, Any]]:
    """Monta o grafo de dependências, opcionalmente recortado.

    O grafo é sempre construído inteiro — resolução de nomes e detecção de
    ciclos valem para o catálogo todo — e só depois recortado pelo escopo
    pedido: a vizinhança de um projeto (`root_id` + `depth`), um domínio ou uma
    solução. Sem recorte, devolve o catálogo inteiro.

    Retorna `None` quando o escopo pedido não existe (projeto, domínio ou
    solução inexistente), para o endpoint responder 404.
    """
    components = list(components)

    by_name: Dict[str, Any] = {}
    for c in components:
        key = _clean(c.name).lower()
        if key:
            by_name.setdefault(key, c)

    nodes: Dict[str, Dict[str, Any]] = {f"c{c.id}": _component_node(c) for c in components}

    edges: List[Dict[str, Any]] = []
    declared: Set[Tuple[str, str]] = set()
    unresolved_ids: Dict[str, str] = {}  # nome normalizado -> id do nó fantasma
    unresolved_names: List[str] = []

    for c in components:
        source_id = f"c{c.id}"
        for dep in c.dependencies:
            target_name = _clean(dep.target_component_name)
            if not target_name:
                continue

            is_ext = getattr(dep, "is_external", False)

            target = by_name.get(target_name.lower()) if not is_ext else None
            if target is not None:
                # Auto-dependência é ruído do manifesto, não uma aresta.
                if target.id == c.id:
                    continue
                target_id = f"c{target.id}"
            else:
                key = target_name.lower()
                if key not in unresolved_ids:
                    node_id = f"u{len(unresolved_ids) + 1}"
                    unresolved_ids[key] = node_id
                    unresolved_names.append(target_name)
                    nodes[node_id] = _unresolved_node(node_id, target_name, is_external=is_ext)
                target_id = unresolved_ids[key]
                if is_ext:
                    nodes[target_id]["is_external"] = True

            if (source_id, target_id) in declared:
                continue
            declared.add((source_id, target_id))
            edges.append(
                {
                    "source": source_id,
                    "target": target_id,
                    "target_name": target_name,
                    "resolved": target is not None,
                    "in_cycle": False,
                    "is_external": is_ext or nodes.get(target_id, {}).get("is_external", False),
                }
            )

    # --- Ciclos: só entre nós resolvidos; um nó fantasma não tem saída. ---
    adjacency: Dict[str, List[str]] = {node_id: [] for node_id in nodes}
    for edge in edges:
        adjacency[edge["source"]].append(edge["target"])

    cycles = _find_cycles(adjacency)
    in_cycle: Set[Tuple[str, str]] = set()
    for cycle in cycles:
        for i, node_id in enumerate(cycle):
            in_cycle.add((node_id, cycle[(i + 1) % len(cycle)]))
    for edge in edges:
        edge["in_cycle"] = (edge["source"], edge["target"]) in in_cycle

    # --- Recorte ---
    undirected: Dict[str, Set[str]] = {node_id: set() for node_id in nodes}
    for edge in edges:
        undirected[edge["source"]].add(edge["target"])
        undirected[edge["target"]].add(edge["source"])

    scope: Dict[str, Any] = {"kind": "catalog", "value": None, "depth": None}
    root_node_id: Optional[str] = None

    if root_id is not None:
        root_node_id = f"c{root_id}"
        if root_node_id not in nodes:
            return None
        visible = _neighbourhood(root_node_id, undirected, depth)
        focus = visible
        scope = {"kind": "root", "value": nodes[root_node_id]["name"], "depth": depth}

    elif domain or solution:
        field = "domain" if domain else "solution"
        target_value = _clean(domain or solution or "").lower()
        focus = {
            f"c{c.id}"
            for c in components
            if _clean(getattr(c, field, None)).lower() == target_value
        }
        if not focus:
            return None
        # Os vizinhos de fora do grupo entram como contexto: uma dependência
        # que cruza a fronteira do domínio é justamente o que interessa ver.
        visible = set(focus)
        for node_id in focus:
            visible |= undirected.get(node_id, set())
        scope = {"kind": field, "value": domain or solution, "depth": None}

    else:
        focus = set(nodes)
        visible = set(nodes)

    # Projeto sem nenhuma dependência declarada não vira caixa solta no
    # diagrama; vira número no rodapé.
    isolated = {
        node_id
        for node_id in visible
        if not undirected.get(node_id) and node_id != root_node_id
    }
    if not include_isolated:
        visible -= isolated

    visible_nodes = []
    for node_id in visible:
        node = dict(nodes[node_id])
        node["in_scope"] = node_id in focus
        node["is_root"] = node_id == root_node_id
        visible_nodes.append(node)
    visible_nodes.sort(key=lambda n: (not n["is_root"], str(n["name"]).lower()))

    visible_edges = [e for e in edges if e["source"] in visible and e["target"] in visible]

    visible_cycles = [
        {"nodes": cycle, "names": [nodes[n]["name"] for n in cycle]} for cycle in cycles
    ]

    return {
        "scope": scope,
        "nodes": visible_nodes,
        "edges": visible_edges,
        "cycles": visible_cycles,
        "unresolved": sorted(unresolved_names, key=str.lower),
        "isolated_count": len(isolated),
        "stats": {
            "components_total": len(components),
            "edges_total": len(edges),
            "nodes_shown": len(visible_nodes),
            "edges_shown": len(visible_edges),
        },
    }
