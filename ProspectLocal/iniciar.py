"""
Script de inicialização do ProspectLocal
Execute: python3 iniciar.py
"""
import subprocess
import sys
import os
import webbrowser
import time

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("""
╔══════════════════════════════════════════════╗
║        🚀 ProspectLocal - Iniciando...       ║
║   Sistema de Prospecção de Empresas Locais   ║
╚══════════════════════════════════════════════╝
""")

# Verificar dependências
try:
    import flask
    from apify_client import ApifyClient
    import reportlab
    print("✅ Dependências OK")
except ImportError as e:
    print(f"⚙️  Instalando dependência faltante: {e}")
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "flask", "apify-client", "reportlab", "--quiet"])
    print("✅ Dependências instaladas! Reiniciando...")
    os.execv(sys.executable, [sys.executable] + sys.argv)

print("🌐 Iniciando servidor em http://localhost:5000")
print("   Pressione CTRL+C para parar\n")

# Iniciar servidor
from app import app, init_db
init_db()
app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
