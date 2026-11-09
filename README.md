# Interview Coach

Private AI interview panel for remote **AI Engineer / AI Architect** roles, published as a website on Render.

- **Login + Register**: one admin (you, set by `ADMIN_USERNAME` / `ADMIN_PASSWORD`). Anyone who registers waits as *pending* until you approve them on the **Admin** page.
- **Mock interview**: one question at a time, honest score /10, gaps, a senior model answer, and the interviewer's cross-question. Voice in/out in Chrome/Edge.
- **Coding round**: 14 Python + 3 SQL problems with real tests. Running code is limited to you and users you mark *trusted*.
- **Coach & doubts**: intro scripts, project showcase scripts, cross-question drills, concept explainers, salary scripts. Export to .md for OneNote.
- **Admin page**: approve, disable or delete users, open or close registration, and set each user's daily AI limit. You are unlimited.

---

## Deploy to Render (one time, about 20 minutes)

### Step 1: Free database (Neon)
Render's free disk is wiped on every restart, so your scores live in a free Postgres database instead.
1. Go to https://neon.tech and sign up with GitHub.
2. Create a project: name `interview-coach`, region **AWS Asia Pacific (Singapore)**.
3. On the dashboard, click **Connect** and copy the connection string. It starts with `postgresql://` and ends with `sslmode=require`. Keep it for Step 3.

### Step 2: Put the code on GitHub (babriteast-business)
1. Go to https://github.com/organizations/babriteast-business/repositories/new (or **New repository** under that account).
   Name: `interview-coach`, **Private**, no README. Click **Create repository**.
2. In PowerShell:
   ```powershell
   cd C:\Users\god\interview-coach
   git init
   git add .
   git commit -m "Interview Coach website"
   git branch -M main
   git remote add origin https://github.com/babriteast-business/interview-coach.git
   git push -u origin main
   ```
   `.env` and the local database are in `.gitignore`, so no secrets reach GitHub.

### Step 3: Create the website on Render
1. Go to https://dashboard.render.com, then **New** → **Blueprint**.
2. Connect GitHub and pick **babriteast-business/interview-coach**. Render reads `render.yaml`.
3. It asks for four values:

   | Key | Value |
   |---|---|
   | `OPENROUTER_API_KEY` | your new OpenRouter key |
   | `ADMIN_USERNAME` | the admin username you were given |
   | `ADMIN_PASSWORD` | the admin password you were given |
   | `DATABASE_URL` | the Neon string from Step 1 |

4. Click **Apply**. The first build takes 2-4 minutes. Your site is at `https://interview-coach-XXXX.onrender.com`.
5. Open it and log in with the admin username and password.

### Updating the site later
Every `git push` redeploys automatically:
```powershell
cd C:\Users\god\interview-coach
git add .
git commit -m "update"
git push
```

### Changing the admin password
Render → your service → **Environment** → edit `ADMIN_PASSWORD` → **Save changes**. It applies on the next restart.

---

## Refresh the question bank from the internet
**On the website (easiest):** Admin → **Refresh from internet**. It pulls the public question lists and asks the AI for this year's most-asked questions per topic, saved in your database. The site also pulls the public lists by itself once a week.

**Or on your PC**, then push:
```powershell
cd C:\Users\god\interview-coach
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe refresh_questions.py              # free: public GitHub question lists
.\.venv\Scripts\python.exe refresh_questions.py --trending 5 # + AI-picked trending questions (needs .env key)
git add data\questions.json; git commit -m "refresh questions"; git push
```

## Import your question guides (one time, after the first deploy)
Admin → **Import questions** → choose the PDF → **Import questions**. Do it once per guide:
- `agentic-ai-interview-questions.pdf`: 223 questions with levels and answer points
- `7_AI_Design_Patterns_Interview_Guide.pdf`: 7 system-design scenarios with what the interviewer is testing

They go into your private database (Neon), so they survive redeploys. PDFs are kept out of GitHub by `.gitignore`.

## Run on your PC instead (optional)
```powershell
cd C:\Users\god\interview-coach
Copy-Item .env.example .env; notepad .env      # fill key + admin login
.\.venv\Scripts\python.exe app.py              # opens http://localhost:8000
```
Leave `DATABASE_URL` empty to use a local file, or paste the Neon string to see the same data as the website.

## Tutorials

The **Tutorials** button (top right of Home, also in the menu) opens your lessons. Each one is a written tutorial with numbered parts, code blocks you can copy, tables, diagrams and highlighted "Say this", "Tip", "Careful" and "Practice" boxes. Your reading position is remembered, and you can mark a lesson as done.

- The lessons live in `tutorials/*.md` and load into your database automatically after each deploy. Edit a `.md` file and push to update that lesson.
- To add a new one, open Tutorials → **Add tutorial** (admin only). Upload a PDF (it's turned into a written lesson automatically) or a Markdown file, then choose a title and a group.
- To remove one, open it and use **Remove this tutorial** at the bottom.

## Good to know
- **Free Render sleeps** after 15 minutes idle. The first visit after that takes about a minute to wake.
- **Free OpenRouter limit**: 20 requests/minute and 50/day, shared by everyone on the site. One graded answer = 1 request; bank questions cost nothing. That's why other users get a daily cap.
- **Trusted users run code on your server.** Their code can't see your API key or database password, but only trust people you know.
- Fill **My profile** with your real projects. The coach builds scripts from it and marks gaps as [FILL] rather than inventing them.
