import uvicorn
import sys
from pathlib import Path

# Adiciona o diretório backend ao sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

if __name__ == "__main__":
    print("==================================================")
    print("Iniciando MovieLens k-NN Recommendation API...")
    print("Acesse no navegador: http://localhost:8000")
    print("Documentação Swagger: http://localhost:8000/docs")
    print("==================================================")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
