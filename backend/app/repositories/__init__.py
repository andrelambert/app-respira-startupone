"""Acesso a dados — a ÚNICA camada que conhece SQL e nomes de tabela (docs/contexto-produto.md §6.4).

Routers e serviços falam com estas funções; o domínio não fala com banco
nenhum. Trocar SQLite por Oracle depois deve mexer só aqui (e nas migrações).
"""
