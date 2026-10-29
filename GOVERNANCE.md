# Governance

How decisions get made, who can approve what, and how you grow from a first pull request to maintainer.

## Roles

| Role | Who | Can |
|---|---|---|
| **Contributor** | Anyone who votes, opens an issue, reviews or sends a pull request | Everything in [CONTRIBUTING.md](CONTRIBUTING.md), from a fork |
| **Collaborator** | Invited after a few merged pull requests | Push branches here (no fork needed), label and assign issues, re-run CI, review. A code owner still approves |
| **Maintainer** | A collaborator listed in [`.github/CODEOWNERS`](.github/CODEOWNERS), for one area or for all of it | Approve and merge pull requests in their area, triage, shape the roadmap |
| **Owner** | [@tomgreef](https://github.com/tomgreef) | Settings, releases, roles and the final say |

Every change reaches `main` through a pull request, and nothing merges while CI is red, whoever wrote it.
A pull request also needs an approval from a code owner of each file it changes. Today the owner is the only code
owner, so the owner approves every pull request. Dependabot's minor and patch updates are the one exception: they
merge themselves once CI is green ([docs/maintaining.md](docs/maintaining.md)).

## Growing your role

There's no application form. Do good work in the open and you'll be asked, or ask in an issue yourself.

1. **Contributor to collaborator:** about three merged pull requests, plus reviews or answers that helped someone.
   The owner sends the invitation.
2. **Collaborator to maintainer:** a few months of steady, kind reviews in one area (the website, Spotify sync, the
   audio code, the tutorials) and good judgement about what *not* to merge. A pull request adds you to `CODEOWNERS`
   for that area, and the owner and the current maintainers approve it.
3. **Maintainer of everything:** someone who looks after several areas can be listed against `*`.

Stepping back is normal. After six months without activity, access is removed with thanks and your name moves to
past maintainers. You're welcome back any time.

## Decisions

- **Small things** are decided in the pull request, by the maintainer who reviews it.
- **What gets built next:** the votes on
  [ideas](https://github.com/tomgreef/dj-toolkit/issues?q=is%3Aissue+is%3Aopen+label%3Aidea+sort%3Areactions-%2B1-desc)
  guide it. The maintainers decide and say why in the issue.
- **Rules and big changes** (a new dependency, the persona, the voice, these roles) start as an issue. If no
  maintainer objects within a week, they go ahead. When people disagree, the owner decides and records it in
  [docs/ux/DECISIONS.md](docs/ux/DECISIONS.md).

## People

- **Owner:** @tomgreef
- **Maintainers:** none yet. This could be you.
- **Past maintainers:** none yet.

## When the project grows

The repository belongs to a personal account, where GitHub has only two levels: the owner, and collaborators who can
write. Once there are more than two maintainers, move it to a free GitHub organization. That adds the Triage and
Maintain roles and teams in `CODEOWNERS`, and old links keep working.
