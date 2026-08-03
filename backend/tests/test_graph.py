"""Testes do grafo de dependências.

`build_graph` só lê atributos dos componentes, então os testes usam dublês em
vez do banco: o que está sob teste é a resolução de nomes, o recorte de escopo
e a detecção de ciclos, não o ORM.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from app.api.graph import build_graph


@dataclass
class FakeDependency:
    target_component_name: str


@dataclass
class FakeComponent:
    id: int
    name: str
    dependencies: List[FakeDependency] = field(default_factory=list)
    kind: str = "Component"
    type: str = "service"
    lifecycle: str = "production"
    owner: str = "time-a"
    domain: Optional[str] = "checkout"
    solution: Optional[str] = "e-commerce"


def make_catalog():
    """Catálogo pequeno com um alvo inexistente e um ciclo."""
    return [
        FakeComponent(1, "pagamento", [FakeDependency("usuario"), FakeDependency("gitlab-api")]),
        FakeComponent(2, "usuario", [FakeDependency("notificacao")]),
        FakeComponent(3, "notificacao", [FakeDependency("pagamento")]),
        FakeComponent(4, "relatorio", [FakeDependency("usuario")], domain="bi", solution="analytics"),
        FakeComponent(5, "sem-dependencia", [], domain="bi", solution="analytics"),
    ]


def test_resolve_nomes_contra_o_catalogo():
    graph = build_graph(make_catalog())
    by_name = {n["name"]: n for n in graph["nodes"]}

    assert by_name["usuario"]["component_id"] == 2
    assert by_name["usuario"]["resolved"] is True

    # O alvo que não existe no catálogo continua no grafo, como nó não resolvido.
    assert by_name["gitlab-api"]["resolved"] is False
    assert by_name["gitlab-api"]["component_id"] is None
    assert graph["unresolved"] == ["gitlab-api"]


def test_projeto_sem_dependencia_fica_fora_do_diagrama():
    graph = build_graph(make_catalog())
    assert "sem-dependencia" not in [n["name"] for n in graph["nodes"]]
    assert graph["isolated_count"] == 1

    incluido = build_graph(make_catalog(), include_isolated=True)
    assert "sem-dependencia" in [n["name"] for n in incluido["nodes"]]


def test_detecta_ciclo():
    graph = build_graph(make_catalog())

    assert len(graph["cycles"]) == 1
    assert sorted(graph["cycles"][0]["names"]) == ["notificacao", "pagamento", "usuario"]

    em_ciclo = {(e["source"], e["target"]) for e in graph["edges"] if e["in_cycle"]}
    assert len(em_ciclo) == 3


def test_recorte_por_raiz_pega_os_dois_sentidos():
    graph = build_graph(make_catalog(), root_id=2, depth=1)
    nomes = sorted(n["name"] for n in graph["nodes"])

    # `usuario` depende de `notificacao` e é consumido por `pagamento` e `relatorio`.
    assert nomes == ["notificacao", "pagamento", "relatorio", "usuario"]
    assert [n["name"] for n in graph["nodes"] if n["is_root"]] == ["usuario"]
    assert graph["scope"] == {"kind": "root", "value": "usuario", "depth": 1}


def test_recorte_por_raiz_respeita_a_profundidade():
    raso = build_graph(make_catalog(), root_id=4, depth=1)
    assert sorted(n["name"] for n in raso["nodes"]) == ["relatorio", "usuario"]

    fundo = build_graph(make_catalog(), root_id=4, depth=2)
    assert "notificacao" in [n["name"] for n in fundo["nodes"]]


def test_recorte_por_dominio_mostra_a_fronteira():
    graph = build_graph(make_catalog(), domain="bi")
    dentro = sorted(n["name"] for n in graph["nodes"] if n["in_scope"])
    fora = sorted(n["name"] for n in graph["nodes"] if not n["in_scope"])

    assert dentro == ["relatorio"]
    # `usuario` é de outro domínio, mas a aresta que cruza a fronteira é o que
    # esta tela existe para mostrar.
    assert fora == ["usuario"]


def test_escopo_inexistente():
    assert build_graph(make_catalog(), root_id=999) is None
    assert build_graph(make_catalog(), domain="nao-existe") is None


def test_auto_dependencia_e_duplicata_nao_viram_aresta():
    catalogo = [
        FakeComponent(1, "solo", [FakeDependency("solo"), FakeDependency("outro"), FakeDependency("Outro")]),
        FakeComponent(2, "outro", []),
    ]
    graph = build_graph(catalogo)
    assert len(graph["edges"]) == 1
    assert graph["edges"][0]["source"] == "c1"
    assert graph["edges"][0]["target"] == "c2"
