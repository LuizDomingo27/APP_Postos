"""
services/git_sync.py
---------------------
Responsabilidade única: persistir o banco SQLite (`Dataset/postos.db`) de volta
no GitHub a cada inserção de dados.

Por que isso existe:
    No Streamlit Community Cloud o disco é EFÊMERO — qualquer gravação no arquivo
    local é apagada quando o app reinicia/dorme. Para os dados sobreviverem, logo
    após cada cadastro o `.db` precisa ser commitado e "empurrado" (push) para o
    GitHub. O push, por sua vez, dispara o redeploy automático do app com os
    dados novos.

Design defensivo:
    - Se não houver secrets configurados (ex.: rodando local sem config) ou se a
      pasta não for um repositório git, a função NÃO lança exceção: retorna
      (False, <motivo>) para que o cadastro em si nunca seja interrompido.
    - O token nunca é logado nem exibido: ele é montado apenas na URL de push,
      em memória, e o `stderr` é sanitizado antes de retornar.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import streamlit as st

from core.config import BASE_DIR, DB_PATH

# Caminho do banco relativo à raiz do repositório (o que o `git add` espera).
_DB_RELATIVE = DB_PATH.relative_to(BASE_DIR).as_posix()


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Executa um comando git capturando saída, sem levantar exceção."""
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _ensure_safe_directory(repo_root: Path) -> None:
    """
    No Streamlit Community Cloud o app roda em um container onde o dono do
    diretório do repositório (clonado pela plataforma) difere do usuário que
    executa o processo Python. O Git recusa operar nesse caso com
    "fatal: detected dubious ownership in repository at '...'", mesmo com o
    token correto — todo comando git (inclusive o `rev-parse` do status)
    falha. Registrar o diretório como seguro evita esse bloqueio; é uma
    operação idempotente e inofensiva em ambiente local.
    """
    _run_git(["config", "--global", "--add", "safe.directory", str(repo_root)], repo_root)


def _read_github_config() -> tuple[dict | None, str]:
    """
    Lê a seção [github] dos secrets do Streamlit.

    Retorna (config, motivo). `config` é None quando o sync está desativado
    (cenário válido em ambiente local); `motivo` explica exatamente O QUE
    falta, em vez de um "não configurado" genérico — o que antes tornava
    impossível diferenciar "esqueci de configurar" de "configurei errado"
    (nome de seção trocado, campo faltando, TOML malformado, etc.).
    """
    try:
        secrets_tem_github = "github" in st.secrets
    except Exception as exc:  # noqa: BLE001 — ex.: secrets.toml malformado
        return None, f"não foi possível ler os Secrets do Streamlit ({exc})"

    if not secrets_tem_github:
        return None, "nenhuma seção [github] encontrada nos Secrets"

    cfg = st.secrets["github"]
    token = cfg.get("token")
    repo = cfg.get("repo")
    faltando = [nome for nome, valor in (("token", token), ("repo", repo)) if not valor]
    if faltando:
        return None, f"seção [github] encontrada, mas faltam os campos: {', '.join(faltando)}"

    return {
        "token": token,
        "repo": repo,
        "branch": cfg.get("branch", "main"),
        "committer_name": cfg.get("committer_name", "App Postos Bot"),
        "committer_email": cfg.get("committer_email", "bot@example.com"),
    }, ""


def _sanitize(text: str, token: str) -> str:
    """Remove o token de qualquer mensagem antes de exibi-la."""
    if not text:
        return ""
    return text.replace(token, "***").strip()


def get_sync_status() -> tuple[bool, str]:
    """
    Verifica, SEM executar nenhuma operação de rede, se a sincronização com o
    GitHub está pronta para funcionar. Serve para exibir um aviso claro na UI.

    Retorna (habilitada, motivo):
      • (True,  "...") quando os secrets estão configurados e é um repo git.
      • (False, "...") com uma explicação amigável do que falta configurar.

    Isso é o que torna a causa da perda de dados VISÍVEL: no Streamlit Cloud o
    disco é efêmero, então se o sync estiver desativado, os cadastros somem no
    próximo reinício — e o usuário precisa saber disso antes de gravar.
    """
    cfg, motivo = _read_github_config()
    if cfg is None:
        return (
            False,
            f"Sincronização com o GitHub DESATIVADA: {motivo}. "
            "No Streamlit Cloud o armazenamento é temporário: novos lançamentos "
            "serão perdidos quando o app reiniciar. Confira a seção [github] em "
            "Settings → Secrets (e reinicie o app após salvar os Secrets).",
        )

    _ensure_safe_directory(BASE_DIR)
    check = _run_git(["rev-parse", "--is-inside-work-tree"], BASE_DIR)
    if check.returncode != 0:
        return (
            False,
            "Sincronização indisponível: a aplicação não está em um repositório git "
            f"({_sanitize(check.stderr, cfg['token']) or 'motivo desconhecido'}).",
        )

    return True, "Sincronização com o GitHub ativa. Novos lançamentos serão persistidos."


def sync_db_to_github(commit_message: str) -> tuple[bool, str]:
    """
    Comita `Dataset/postos.db` e dá push para o GitHub.

    Retorna (sucesso, mensagem). Nunca levanta exceção: falhas viram (False, msg)
    para não interromper o fluxo de cadastro.
    """
    cfg, motivo = _read_github_config()
    if cfg is None:
        return False, f"Sincronização desativada: {motivo}."

    repo_root = BASE_DIR
    token = cfg["token"]
    branch = cfg["branch"]

    # 0. Confirma que estamos dentro de um repositório git.
    _ensure_safe_directory(repo_root)
    check = _run_git(["rev-parse", "--is-inside-work-tree"], repo_root)
    if check.returncode != 0:
        return False, (
            "Sincronização indisponível: a pasta não é um repositório git "
            f"({_sanitize(check.stderr, token) or 'motivo desconhecido'})."
        )

    # 1. Identidade do committer (necessária em clone novo, como no Cloud).
    _run_git(["config", "user.name", cfg["committer_name"]], repo_root)
    _run_git(["config", "user.email", cfg["committer_email"]], repo_root)

    # 2. Stage do banco. Se nada mudou, não há o que sincronizar.
    add = _run_git(["add", _DB_RELATIVE], repo_root)
    if add.returncode != 0:
        return False, _sanitize(add.stderr, token) or "Falha ao adicionar o banco ao git."

    status = _run_git(["status", "--porcelain", _DB_RELATIVE], repo_root)
    if not status.stdout.strip():
        return True, "Nenhuma mudança no banco para sincronizar."

    # 3. Commit.
    commit = _run_git(["commit", "-m", commit_message], repo_root)
    if commit.returncode != 0:
        return False, _sanitize(commit.stderr, token) or "Falha ao commitar."

    # 4. Atualiza a base remota (melhor esforço). O .db é binário e não tem merge;
    #    em conflito, abortamos o rebase e pedimos nova tentativa.
    push_url = f"https://{token}@github.com/{cfg['repo']}.git"
    fetch = _run_git(["fetch", push_url, branch], repo_root)
    if fetch.returncode == 0:
        rebase = _run_git(["rebase", "FETCH_HEAD"], repo_root)
        if rebase.returncode != 0:
            _run_git(["rebase", "--abort"], repo_root)
            return (
                False,
                "Conflito ao sincronizar (alguém gravou ao mesmo tempo). "
                "O registro foi gravado localmente — recarregue e tente o sync novamente.",
            )

    # 5. Push para o GitHub.
    push = _run_git(["push", push_url, f"HEAD:{branch}"], repo_root)
    if push.returncode != 0:
        return False, _sanitize(push.stderr, token) or "Falha ao enviar (push) para o GitHub."

    return True, "Dados sincronizados com o GitHub."
