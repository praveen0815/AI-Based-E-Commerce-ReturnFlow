# Push ReturnFlow to GitHub

## Why `remote: Repository not found` happens

GitHub returns this when **the repository does not exist yet** on github.com, or your account **cannot access** it (wrong login, private repo, typo in URL).

Your local repo is ready (`main` at commit `1c915cd`). Remote is set to:

`https://github.com/praveen0815/ReturnFlow.git`

## Fix (one-time)

### 1. Create the empty repository on GitHub

1. Sign in as **praveen0815** at [github.com](https://github.com).
2. Open **New repository**: https://github.com/new  
3. **Repository name:** `ReturnFlow` (match the URL casing).  
4. **Do not** add a README, `.gitignore`, or license (you already have them locally).  
5. Create the repository.

### 2. Authenticate Git (if prompted)

Windows usually uses **Git Credential Manager**. When you push, sign in with the same GitHub account that owns the repo.

### 3. Push from the project root

```powershell
cd C:\AI-Projects\ReturnFlow
git remote -v
git push -u origin main
```

If you already added `origin` twice, only fix the URL:

```powershell
git remote set-url origin https://github.com/praveen0815/ReturnFlow.git
git push -u origin main
```

### 4. Optional: GitHub CLI

```powershell
winget install GitHub.cli
gh auth login
gh repo create ReturnFlow --public --source=. --remote=origin --push
```

Use `--private` instead of `--public` if you prefer a private repo.

## Security check before push

- `.env` must **not** be tracked (`git check-ignore -v .env` should list `.gitignore`).
- No `data/` uploads or Chroma indexes in the commit.

```powershell
git check-ignore -v .env
git status
```

## PowerShell note

Do not paste stray characters like `]` on a new line after `git remote set-url` — that was a separate invalid command in your terminal log.