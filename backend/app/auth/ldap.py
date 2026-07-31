import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class LDAPAuthService:
    @staticmethod
    def test_connection(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Testa a conexão com o servidor LDAP usando as configurações fornecidas.
        """
        host = config.get("server_host", "").strip()
        port = int(config.get("server_port", 389))
        use_ssl = bool(config.get("use_ssl", False))
        bind_dn = config.get("bind_dn", "").strip()
        bind_password = config.get("bind_password", "")

        if not host:
            return {"success": False, "message": "O endereço do servidor LDAP (Host) é obrigatório."}

        try:
            import ldap3
            from ldap3 import Server, Connection, ALL

            server = Server(host, port=port, use_ssl=use_ssl, get_info=ALL, connect_timeout=5)
            
            if bind_dn:
                conn = Connection(server, user=bind_dn, password=bind_password, auto_bind=True, receive_timeout=5)
            else:
                conn = Connection(server, auto_bind=True, receive_timeout=5)
                
            conn.unbind()
            return {"success": True, "message": "Conexão com o servidor LDAP estabelecida com sucesso!"}
        except ImportError:
            import socket
            try:
                sock = socket.create_connection((host, port), timeout=5)
                sock.close()
                return {"success": True, "message": "Servidor LDAP alcançável via TCP (pacote ldap3 não instalado, teste de porta bem-sucedido)."}
            except Exception as e:
                return {"success": False, "message": f"Erro de conexão com o servidor {host}:{port} - {str(e)}"}
        except Exception as e:
            return {"success": False, "message": f"Falha na conexão LDAP: {str(e)}"}

    @staticmethod
    def authenticate(config: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
        """
        Autentica um usuário via LDAP.
        """
        if not config.get("enabled", False):
            return {"success": False, "message": "A autenticação LDAP está desativada nas configurações."}

        host = config.get("server_host", "").strip()
        port = int(config.get("server_port", 389))
        use_ssl = bool(config.get("use_ssl", False))
        bind_dn = config.get("bind_dn", "").strip()
        bind_password = config.get("bind_password", "")
        base_dn = config.get("base_dn", "").strip()
        user_attribute = config.get("user_attribute", "uid").strip() or "uid"

        if not host or not base_dn:
            return {"success": False, "message": "Configuração do LDAP incompleta no servidor."}

        if not username or not password:
            return {"success": False, "message": "Usuário e senha são obrigatórios."}

        try:
            import ldap3
            from ldap3 import Server, Connection, ALL, SUBTREE

            server = Server(host, port=port, use_ssl=use_ssl, get_info=ALL, connect_timeout=5)
            
            # 1. Bind com conta de serviço (ou anônimo) para buscar a DN do usuário
            if bind_dn:
                conn = Connection(server, user=bind_dn, password=bind_password, auto_bind=True, receive_timeout=5)
            else:
                conn = Connection(server, auto_bind=True, receive_timeout=5)

            # 2. Monta filtro de busca do usuário
            search_filter = f"({user_attribute}={username})"
            conn.search(
                search_base=base_dn,
                search_filter=search_filter,
                search_scope=SUBTREE,
                attributes=['cn', 'displayName', 'mail', 'sn', 'givenName', user_attribute]
            )

            if not conn.entries:
                conn.unbind()
                return {"success": False, "message": "Usuário não encontrado no diretório LDAP."}

            user_entry = conn.entries[0]
            user_dn = user_entry.entry_dn
            
            display_name = username
            if hasattr(user_entry, 'displayName') and user_entry.displayName:
                display_name = str(user_entry.displayName)
            elif hasattr(user_entry, 'cn') and user_entry.cn:
                display_name = str(user_entry.cn)

            email = str(user_entry.mail) if hasattr(user_entry, 'mail') and user_entry.mail else ""
            conn.unbind()

            # 3. Tenta efetuar o bind com a DN do usuário e a senha fornecida
            user_conn = Connection(server, user=user_dn, password=password, receive_timeout=5)
            if not user_conn.bind():
                return {"success": False, "message": "Senha do usuário LDAP incorreta."}
            
            user_conn.unbind()

            return {
                "success": True,
                "user": {
                    "username": username,
                    "name": display_name,
                    "email": email,
                    "dn": user_dn
                }
            }

        except ImportError:
            return {"success": False, "message": "Módulo ldap3 não instalado no servidor backend."}
        except Exception as e:
            logger.error(f"Erro ao autenticar no LDAP: {e}")
            return {"success": False, "message": f"Erro na autenticação LDAP: {str(e)}"}
