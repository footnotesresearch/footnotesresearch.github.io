# Footnote — research archive site

A small website that publishes your forensic reports with a date and a
source for every finding. GitHub stores the files, keeps a public history of
every change (your proof of when each report went up), and hosts the site
for free.

You write in plain text files. GitHub turns them into the website
automatically, about a minute after each change.

---

## Part 1: put the site online (one time, about 15 minutes)

1. **Create a GitHub account** at github.com. Pick a username you're happy
   to have in the web address, since the site will live at
   `your-username.github.io/footnote` until you buy a domain.

2. **Create a repository** (GitHub's word for a project folder).
   Click **+** at the top right, then **New repository**.
   Name it `footnote`, choose **Public**, and click **Create repository**.

3. **Upload the files.** On the new repository page, click
   **uploading an existing file**. Unzip the folder I sent, open it, select
   everything inside it, and drag it all onto the page. Click
   **Commit changes**.

4. **Add the publishing instructions.** Folders starting with a dot are often
   hidden on a Mac or PC, so this one may not have uploaded. Check: if you
   don't see a `.github` folder in your repository, click **Add file**, then
   **Create new file**. Type this exact name:
   `.github/workflows/publish.yml`
   then open `setup/publish.yml` from the zip, copy everything in it, paste
   it in, and click **Commit changes**.

5. **Turn on the website.** Go to **Settings**, then **Pages** (left menu).
   Under **Source**, choose **GitHub Actions**.

6. **Point the site at your repository.** Open `site.yml`, click the pencil
   icon to edit, and change the `repo_url` line to your repository's
   address, for example `https://github.com/your-username/footnote`.
   Commit the change.

7. **Wait a minute**, then open the **Actions** tab. A green tick means the
   site is live at `https://your-username.github.io/footnote`.

At this point the site will be live but empty, with the message that the first
reports are being checked. That's expected: the Himadri and Ather pages are
drafts and stay off the public site until you publish them.

---

## Part 2: publish your first reports

Each company has one page file, and each report has its own file.

| What | Where |
|---|---|
| Company pages | `content/companies/` |
| Reports | `content/reports/` |
| Downloadable spreadsheets | `content/data/<company>/` |
| About and disclaimer | `content/pages/about.md` |
| Site name, author, disclaimer | `site.yml` |
| Sectors | `sectors.yml` |

To publish Himadri:

1. Open `content/companies/himadri-speciality-chemical.md` and click the
   pencil icon.
2. Replace every **[bracketed]** placeholder with the real fact, figure or
   link. The takeaways I started are worded from your earlier findings and
   need your numbers and sources.
3. Fill in `author_position` honestly, for example `None`.
4. Change `status: draft` to `status: published`.
5. Click **Commit changes**. Do the same for the report file in
   `content/reports/`.

The site refuses to build if a file marked `published` still has a
[bracketed] placeholder, a takeaway with no source, or a source number that
doesn't exist. If something is wrong, the **Actions** tab shows a red cross;
click it to read the message, which says exactly which file and line to fix.
The live site stays as it was until you fix it.

### Adding a new company

Copy an existing company file, give it a new name in lowercase with
hyphens (e.g. `apollo-hospitals.md`), and change the details. The `sector`
line must match a `slug` in `sectors.yml`: `energy`, `healthcare`,
`financial-services`, `chemicals` or `automobiles`.

### Adding a new report

Create a file in `content/reports/` named with the date first, for example
`2026-11-04-himadri-q2-fy27.md`. Copy the top section from an existing
report. The `company` line must match the company file's name without `.md`.

### Writing takeaways

Each takeaway has a short topic, one or two sentences of fact, and the
numbers of its sources:

```yaml
  - topic: Debt
    text: Net debt fell from ₹1,200 crore in FY22 to ₹300 crore in FY26.
    sources: [1, 4]
```

About ten is the aim, not a rule. If a company only listed recently, it will
have fewer. Phrase price movements as sequence, not cause: "the share price
rose after X", not "X caused the rise".

---

## What the site does for AI tools

You don't need to do anything for these; they're built on every change.

- `llms.txt`: a contents page written for AI tools.
- `llms-full.txt`: the whole archive in one plain-text file.
- A `.md` plain-text version of every company and report page.
- `reports.json`: every company, takeaway and report as structured data.
- Hidden labels on each page (schema.org) giving company, sector, author
  and publication date.
- `robots.txt` that explicitly welcomes search engines and AI crawlers.
- `sitemap.xml` and an RSS-style feed for new reports.

---

## Changing the name later

Edit `name:` in `site.yml`. Every page updates. If you buy a domain, GitHub's
Pages settings have a **Custom domain** box; the site adjusts its links
automatically.

## Before you launch

- Have a securities lawyer read the disclaimer in `site.yml` and
  `content/pages/about.md`. I wrote it to fit your plan (factual analysis,
  no recommendations), but I'm not a lawyer, and SEBI's research analyst
  rules are worth a professional check.
- Make sure no takeaway reads as a recommendation or a price view.

## Previewing on your own computer (optional)

If you have Python installed:

```
pip install -r requirements.txt
python build.py --serve
```

then open http://localhost:8000. Preview mode shows drafts with a yellow
"Draft" label; the public site never does.
