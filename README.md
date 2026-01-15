# DaitDanyang Backend

## 🚀 배포 가이드
이 프로젝트는 **Hugging Face Spaces (Docker)** 에 배포됩니다.
GitHub Actions를 통해 `back/` 폴더의 내용이 자동으로 Space로 동기화됩니다.

- **Engine**: Python Flask + RAG (Vector Search)
- **Database**: SQLite (managed via Hugging Face Datasets)
- **Deployment**: GitHub Actions + `huggingface_hub` (Python Script)