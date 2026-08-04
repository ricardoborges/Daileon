"""Agregação de componentes por dimensão organizacional (domínio, solução).

Domínio e solução não são tabelas: são campos declarados no `project-info.yml`
de cada componente. As duas listagens são, portanto, a mesma operação —
agrupar os componentes por um campo e derivar a dimensão cruzada — e ficam
aqui uma vez só em vez de duplicadas por endpoint.
"""

from typing import Any, Dict, Iterable, List, Literal

GroupKey = Literal["domain", "solution"]

# Como cada dimensão se descreve: o campo agrupador, o nome que ele recebe na
# resposta e a dimensão cruzada listada dentro de cada grupo.
_DIMENSIONS: Dict[GroupKey, Dict[str, str]] = {
    "domain": {"field": "domain", "label": "domain", "cross_field": "solution", "cross_label": "solutions"},
    "solution": {"field": "solution", "label": "solution", "cross_field": "domain", "cross_label": "domains"},
}


def _clean(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def component_summary(c, detailed: bool = False) -> Dict[str, Any]:
    """Resumo de um componente para as listagens agregadas.

    `detailed=True` adiciona os campos que só a tela de detalhe usa, evitando
    carregar tags e deployments de todo o catálogo na listagem.
    """
    summary: Dict[str, Any] = {
        "id": c.id,
        "gitlab_project_id": c.gitlab_project_id,
        "name": c.name,
        "description": c.description,
        "kind": c.kind,
        "type": c.type,
        "lifecycle": c.lifecycle,
        "owner": c.owner,
        "domain": c.domain,
        "solution": c.solution,
        "system": c.system,  # legado: alias de `solution`, será removido
        "gitlab_url": c.gitlab_url,
        "has_manifest": c.has_manifest,
        "docs_count": c.docs_count,
    }
    if detailed:
        summary["tags"] = [t.name for t in c.tags]
        summary["deployments_count"] = len(c.deployments)
    return summary


def group_components(components: Iterable[Any], key: GroupKey) -> List[Dict[str, Any]]:
    """Agrupa componentes por domínio ou por solução.

    Componentes sem o campo preenchido ficam de fora: um domínio em branco não
    é um domínio, e criar um grupo vazio geraria uma página de detalhe sem URL
    possível. A tela de projetos é quem oferece o filtro "sem domínio".
    """
    dim = _DIMENSIONS[key]
    groups: Dict[str, Dict[str, Any]] = {}

    for c in components:
        group_name = _clean(getattr(c, dim["field"], None))
        if not group_name:
            continue

        # A primeira grafia encontrada vira a canônica; o agrupamento em si é
        # case-insensitive para não partir "Strix" e "strix" em dois grupos.
        group_id = group_name.lower()
        if group_id not in groups:
            groups[group_id] = {
                dim["label"]: group_name,
                dim["cross_label"]: set(),
                "owners": set(),
                "components": [],
            }

        g = groups[group_id]
        cross_value = _clean(getattr(c, dim["cross_field"], None))
        if cross_value:
            g[dim["cross_label"]].add(cross_value)
        if c.owner:
            g["owners"].add(c.owner)
        g["components"].append(component_summary(c))

    result = []
    for g in groups.values():
        entry = {
            dim["label"]: g[dim["label"]],
            dim["cross_label"]: sorted(g[dim["cross_label"]]),
            "owners": sorted(g["owners"]),
            "components_count": len(g["components"]),
            "components": g["components"],
        }
        if key == "domain":
            entry["systems"] = entry["solutions"]  # legado
        result.append(entry)

    result.sort(key=lambda x: str(x[dim["label"]]).lower())
    return result


def build_group_detail(components: Iterable[Any], key: GroupKey, name: str) -> Dict[str, Any]:
    """Monta o detalhe de um domínio ou solução, ou `None` se não existir."""
    dim = _DIMENSIONS[key]
    target = _clean(name).lower()

    canonical = ""
    cross_values = set()
    owners = set()
    matched = []

    for c in components:
        group_name = _clean(getattr(c, dim["field"], None))
        if not group_name or group_name.lower() != target:
            continue

        if not canonical:
            canonical = group_name
        cross_value = _clean(getattr(c, dim["cross_field"], None))
        if cross_value:
            cross_values.add(cross_value)
        if c.owner:
            owners.add(c.owner)
        matched.append(component_summary(c, detailed=True))

    if not matched:
        return None

    detail = {
        dim["label"]: canonical or name,
        dim["cross_label"]: sorted(cross_values),
        "owners": sorted(owners),
        "components_count": len(matched),
        "components": matched,
    }
    if key == "domain":
        detail["systems"] = detail["solutions"]  # legado
    return detail
