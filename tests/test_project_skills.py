import unittest
from unittest.mock import patch, mock_open, MagicMock
import kuri_skills.project_assistant as pa
import kuri_skills.social_monitor as sm

class TestProjectAssistantSkills(unittest.TestCase):

    @patch("kuri_skills.project_assistant._run_git_cmd")
    @patch("os.path.exists")
    def test_git_status_repo_active(self, mock_exists, mock_run_git):
        """Verifica o status git quando o diretório é um repositório ativo com alterações."""
        mock_exists.return_value = True
        mock_run_git.side_effect = ["main", "M main.py\n?? new_file.txt"]
        
        result = pa.git_status()
        self.assertIn("Branch atual: main", result)
        self.assertIn("Alterações pendentes:", result)
        self.assertIn("M main.py", result)

    @patch("kuri_skills.project_assistant._run_git_cmd")
    @patch("os.path.exists")
    def test_git_status_repo_clean(self, mock_exists, mock_run_git):
        """Verifica o status git quando o repositório está limpo."""
        mock_exists.return_value = True
        mock_run_git.side_effect = ["main", ""]
        
        result = pa.git_status()
        self.assertIn("Branch: main", result)
        self.assertIn("Tudo limpo", result)

    @patch("os.path.exists")
    def test_git_status_not_a_repo(self, mock_exists):
        """Verifica comportamento quando o diretório não é repositório Git."""
        mock_exists.return_value = False
        result = pa.git_status(repo_path="C:/fake/path")
        self.assertIn("não parece ser um repositório Git", result)

    @patch("os.path.exists")
    @patch("os.path.isdir")
    @patch("os.listdir")
    def test_listar_projetos_desenvolvimento(self, mock_listdir, mock_isdir, mock_exists):
        """Verifica listagem correta de subpastas contendo .git."""
        mock_exists.side_effect = lambda path: "Projetos" in path.replace("\\", "/") and ("NaoGit" not in path.replace("\\", "/"))
        mock_isdir.return_value = True
        mock_listdir.return_value = ["ProjetoA", "ProjetoB", "NaoGit"]
        
        result = pa.listar_projetos_desenvolvimento(diretorio_base="C:/Projetos")
        self.assertIn("ProjetoA", result)
        self.assertIn("ProjetoB", result)
        self.assertNotIn("NaoGit", result)

    @patch("os.path.exists")
    def test_resumo_projeto_not_found(self, mock_exists):
        """Verifica retorno caso o README não exista."""
        mock_exists.return_value = False
        result = pa.resumo_projeto(projeto_path="C:/fake/path")
        self.assertIn("não encontrado", result)

    @patch("os.path.exists")
    def test_resumo_projeto_content(self, mock_exists):
        """Verifica leitura correta e resumo do README.md."""
        # Se bater no README.md, existe.
        mock_exists.side_effect = lambda path: "README.md" in path or "path" in path
        
        m_open = mock_open(read_data="# Meu Projeto\nEste projeto faz coisas incríveis.")
        with patch("builtins.open", m_open):
            result = pa.resumo_projeto(projeto_path="C:/path")
            
        self.assertIn("Conteúdo do README.md", result)
        self.assertIn("Este projeto faz coisas incríveis.", result)

class TestSocialMonitorSkills(unittest.TestCase):

    @patch("httpx.get")
    def test_obter_reddit_hot_success(self, mock_get):
        """Verifica a extração correta de posts reais do Reddit AI/Python."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "Grok 4 is amazing",
                            "score": 150,
                            "url": "https://reddit.com/grok"
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        result = sm._obter_reddit_hot("LocalLlama")
        self.assertIn("[LocalLlama] Grok 4 is amazing", result)
        self.assertIn("Likes: 150", result)

    @patch("kuri_skills.social_monitor._obter_reddit_hot")
    def test_checar_redes_sociais_todas(self, mock_reddit):
        """Verifica se o relatório contém todas as seções."""
        mock_reddit.return_value = "- [Reddit] Mock Post"
        
        result = sm.checar_redes_sociais(plataforma="todas")
        self.assertIn("Reddit AI & Python Trends", result)
        self.assertIn("=== YouTube ===", result)
        self.assertIn("Não vou inventar vídeo", result)
        self.assertIn("Twitter/X: sem API", result)

if __name__ == "__main__":
    unittest.main()
