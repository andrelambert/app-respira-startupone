import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException, Response, status

from app.config import get_settings
from app.models import Usuario
from app.repositories import consentimentos as repo_c
from app.repositories import usuarios as repo_u
from app.routers.comum import SessionDep, UsuarioDep
from app.schemas import ConfigOut, LoginEntrada, RegistroEntrada, UsuarioAtualizar, UsuarioOut
from app.services import auth, conexao
from app.services.contexto import hoje_do_usuario

log = logging.getLogger("respira.auth")
router = APIRouter(tags=["conta"])


def _out(u: Usuario) -> UsuarioOut:
    return UsuarioOut(
        apelido=u.apelido,
        email=u.email,
        nome_completo=u.nome_completo,
        demo=u.demo,
        tem_identificacao=bool(u.cpf and u.nome_completo),
        # Só os 3 primeiros e os 2 últimos dígitos: o suficiente para reconhecer.
        cpf_mascarado=f"{u.cpf[:3]}.***.***-{u.cpf[-2:]}" if u.cpf else None,
        ja_desistiu_de_plano=u.ja_desistiu_de_plano,
        meses_simulados=u.meses_simulados,
        hoje=hoje_do_usuario(u),
    )


def _logar(s: SessionDep, u: Usuario, resposta: Response) -> UsuarioOut:
    token, max_age = auth.abrir_sessao(s, u)
    resposta.set_cookie(
        auth.COOKIE,
        token,
        max_age=max_age,
        httponly=True,  # JavaScript não lê o token
        samesite="lax",
        secure=get_settings().cookie_seguro,
        path="/",
    )
    return _out(u)


@router.get("/config", response_model=ConfigOut)
def config(s: SessionDep) -> ConfigOut:
    cfg = get_settings()
    demo = cfg.demo_configurada() and cfg.demo_email is not None and repo_u.por_email(s, cfg.demo_email) is not None
    return ConfigOut(
        demo_disponivel=demo,
        belvo_configurada=cfg.belvo_configurada(),
        webhooks=cfg.belvo_webhooks_enabled,
    )


@router.post("/auth/registrar", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def registrar(dados: RegistroEntrada, s: SessionDep, resposta: Response) -> UsuarioOut:
    if repo_u.por_email(s, dados.email) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="email_em_uso")
    if repo_u.por_cpf(s, dados.cpf) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="cpf_em_uso")
    u = repo_u.criar(
        s,
        Usuario(
            uuid_externo=str(uuid.uuid4()),  # external_id da Belvo: UUID sem PII (§7.3)
            email=dados.email,
            senha_hash=auth.hash_senha(dados.senha),
            apelido=dados.nome_completo.split()[0][:60],
            nome_completo=dados.nome_completo,
            cpf=dados.cpf,
            ja_desistiu_de_plano=dados.ja_desistiu_de_plano,
        ),
    )
    return _logar(s, u, resposta)


@router.post("/auth/entrar", response_model=UsuarioOut)
def entrar(dados: LoginEntrada, s: SessionDep, resposta: Response) -> UsuarioOut:
    try:
        u = auth.autenticar(s, dados.email, dados.senha)
    except auth.LoginBloqueado as e:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="muitas_tentativas") from e
    if u is None:
        # Mesma resposta para e-mail inexistente e senha errada.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="credenciais_invalidas")
    return _logar(s, u, resposta)


@router.post("/auth/demo", response_model=UsuarioOut)
def entrar_demo(s: SessionDep, resposta: Response) -> UsuarioOut:
    """Atalho da apresentação: entra na conta fictícia da Juliana."""
    cfg = get_settings()
    u = repo_u.por_email(s, cfg.demo_email or "") if cfg.demo_configurada() else None
    if u is None or not u.demo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="demo_indisponivel")
    return _logar(s, u, resposta)


@router.post("/auth/sair", status_code=status.HTTP_204_NO_CONTENT)
def sair(
    s: SessionDep,
    resposta: Response,
    respira_sessao: Annotated[str | None, Cookie()] = None,
) -> None:
    auth.fechar_sessao(s, respira_sessao)
    resposta.delete_cookie(auth.COOKIE, path="/", samesite="lax", secure=get_settings().cookie_seguro, httponly=True)


@router.get("/usuarios/me", response_model=UsuarioOut)
def me(u: UsuarioDep) -> UsuarioOut:
    return _out(u)


@router.patch("/usuarios/me", response_model=UsuarioOut)
def atualizar(dados: UsuarioAtualizar, u: UsuarioDep, s: SessionDep) -> UsuarioOut:
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(u, campo, valor)
    return _out(repo_u.salvar(s, u))


@router.delete("/usuarios/me", status_code=status.HTTP_204_NO_CONTENT)
async def excluir(u: UsuarioDep, s: SessionDep, resposta: Response) -> None:
    """Exclusão de conta e dados (§9 /privacidade): revoga todo link na Belvo
    e apaga tudo localmente. A conta demo não é excluída — use "reiniciar"."""
    if u.demo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="conta_demo")
    assert u.id is not None
    for c in repo_c.listar(s, u.id):
        if c.link_externo:
            try:
                await conexao.revogar(s, c)
            except conexao.ErroConexao as e:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail=e.codigo) from e
    repo_u.apagar_tudo(s, u.id)
    resposta.delete_cookie(auth.COOKIE, path="/", samesite="lax", secure=get_settings().cookie_seguro, httponly=True)
