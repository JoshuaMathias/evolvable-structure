# Install the skill

The author's own `evolvable-structure` skill is published here as a complete, self-contained folder: `skill/evolvable-structure/`.
It is plain markdown, starting from `SKILL.md`, which is written by Joshua and is the authority; `INDEX.md` routes to the other files.
It needs no repository checkout, no Python and no knowledge of any other project. Pick one way.

## 1. Claude Code plugin marketplace

```
/plugin marketplace add JoshuaMathias/evolvable-structure
/plugin install evolvable-structure@esoi
```

Update later with `/plugin marketplace update esoi`. From a shell the same steps are `claude plugin marketplace add
JoshuaMathias/evolvable-structure` and `claude plugin install evolvable-structure@esoi`.

## 2. Download the folder (no code)

For every project of yours (one folder under your home):

```bash
mkdir -p ~/.claude/skills/evolvable-structure && curl -L https://codeload.github.com/JoshuaMathias/evolvable-structure/tar.gz/main | tar -xz --strip-components=3 -C ~/.claude/skills/evolvable-structure evolvable-structure-main/skill/evolvable-structure
```

For one project, run the same line from its root with `./.claude/skills/evolvable-structure` in place of
`~/.claude/skills/evolvable-structure`. Run it again to update; it overwrites the files it ships.

## 3. The `esoi` command

```bash
pip install "esoi @ git+https://github.com/JoshuaMathias/evolvable-structure.git#subdirectory=implementations/python"
esoi skill install                      # into ~/.claude/skills/evolvable-structure
esoi skill install --project PATH       # into PATH/.claude/skills/evolvable-structure
esoi skill install --dest DIR           # into DIR/evolvable-structure, for an agent with another skills folder
```

The command installs the copy bundled in the package. It stops if a different skill is already there; `--force` replaces it.

## Other agents

The skill is plain markdown. An agent that reads a skills folder can use it where it is; any other agent can be pointed at
`SKILL.md` (and told to open `INDEX.md` for detail) as standing instructions or a first message.

## Where the copy comes from

The skill is generated from the author's private skill, so there is one source of truth. Do not edit the copy by hand:
`esoi skill sync` overwrites it and `esoi skill check` fails when it is stale or leaks anything private. To use a different
source or add your own private terms, set `ESOI_SKILL_SOURCE` and `ESOI_SKILL_DENYLIST`; see
[implementations/python/esoi/skill.py](../../implementations/python/esoi/skill.py) for the configuration.
