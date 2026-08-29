# cs7-claude-plugins

A [Claude Code](https://claude.ai/code) plugin marketplace providing two-phase PDCA development, and AI-powered image and video generation using Google's Gemini API.

## Plugins

### pdca

Two-phase development, the Deming PDCA cycle with a session boundary in the middle. **Plan** is an interactive session that verifies its assumptions by running commands and produces a self-sufficient plan file. **Do / Check / Act** is a *fresh* session — optionally a different model at a different effort level — that implements that plan unattended under Claude Code's `/goal`.

The plan file is the only interface between the phases, which is why the skill pushes on facts recorded with the command that verified them, acceptance criteria that are runnable commands, and an execution protocol the executing session can follow alone.

**Commands:**

| Command | Purpose |
|---|---|
| `/pdca:plan [model] [effort] <goal or plan path>` | Plan interactively, then hand off to an autonomous run |

**Skills:**

| Skill | Trigger | Capabilities |
|---|---|---|
| `plan` | "plan before implementing", "write a plan I can run later", "too big for one session", "hand this off", "PDCA" | Verified-context planning, adversarial review by the executing model, `/goal` condition construction, resumable plan files |

- Before handoff, the plan is reviewed by a fresh `claude -p` at phase 2's model and effort — it sees the plan and the repo and nothing else — looping until both models agree or three rounds pass
- The goal condition inlines the acceptance criteria, stays inside the 4000-character cap, is shell-safe, and always carries a blocked-report escape hatch so an impossible check terminates instead of looping
- The handoff command is written into the plan itself, so it survives weeks between the two phases
- The autonomous session opens with a pre-flight gate — that a `/goal` naming its plan is driving it, on the right model, effort and permission mode, on the right branch, with every privilege the tasks need — all confirmed before anything changes; a mismatch is a blocked report in turn 1, not an adaptation
- Every run asks for a Jira ticket in the opening interview; given one, phase 1 treats it as a request rather than a specification and plans against its requirements, and phase 2 closes it out — the finished plan committed, the outcome commented with a link to it in git history — before anything is deleted
- The plan file self-destructs when the work is done

### gemini-media

Generate and edit images and videos directly from Claude Code using Google's Gemini models — commonly known as **Nano Banana** (image generation) and **Veo** (video generation).

**Skills:**

| Skill | Trigger | Models |
|---|---|---|
| `generate-image` | "generate an image", "edit this image", "refine the image" | Nano Banana (Gemini 3.1 Flash, Gemini 3 Pro, Gemini 2.5 Flash) |
| `generate-video` | "generate a video", "animate this image", "extend the video" | Veo 3.1, Veo 3 |

#### Image Generation

- Text-to-image generation
- Image editing with up to 14 reference images
- Multi-turn conversational editing with session persistence
- Google Search grounding for real-world subjects
- Automatic thinking mode for complex prompts
- Aspect ratios from 1:1 to 21:9, resolutions up to 4K
- PNG or JPEG output with configurable compression

#### Video Generation

- Text-to-video generation
- Image-to-video animation
- Frame interpolation between two images
- Video extension (up to 20 extensions per chain)
- Reference images for style/content guidance (up to 3)
- Native audio synthesis
- 720p to 4K, 4-8 second clips
- Async generation with background submission and polling

## Installation

Both plugins need [Claude Code](https://claude.ai/code) v1.0.33+. Add the marketplace once:

```bash
claude plugin marketplace add christian-schlichtherle/cs7-claude-plugins
```

Then install whichever plugins you want:

```bash
claude plugin install pdca@cs7-claude-plugins
claude plugin install gemini-media@cs7-claude-plugins
```

### pdca

Nothing to configure, but `/goal` needs a trusted workspace with hooks enabled — it is unavailable when `disableAllHooks` or `allowManagedHooksOnly` is set in your settings.

### gemini-media

Needs Python 3.7+ (the scripts use only stdlib, so no `pip install`) and a [Gemini API Key](https://aistudio.google.com/api-keys) from Google's AI Studio:

```bash
export GEMINI_API_KEY='your-key-here'
```

Or create a `.env` file in the directory where you run Claude Code:

```
GEMINI_API_KEY=your-key-here
```

## Usage

### pdca

Start the interactive planning phase, naming the model and effort level for the autonomous phase that follows:

```
/pdca:plan opus high raise the staging cache TTL from five minutes to an hour
```

Anything missing — model, effort, permission mode, and the Jira ticket, which is
asked for every time — is settled in a short interview of pick-an-option questions
before planning starts. Each turn then updates a plan file and reports only what
changed. When you are satisfied, the plan is reviewed by a fresh session at the executing
model's level; whatever the review changed comes back to you, and only a version
that you, the planning session and the executing model all stand behind — or that
you explicitly cleared over the reviewer's objection — gets the command to run the
implementation unattended.

### gemini-media

The skills activate automatically when you ask Claude Code to generate media:

```
> Generate an image of a steampunk cityscape at sunset in 16:9

> Edit the image — add a dirigible in the sky

> Generate a video of a camera slowly flying through the city
```

The skills handle model selection, prompt optimization, and output management. Generated files are saved to `./generated-images/` and `./generated-videos/` in your working directory and auto-opened on macOS.

## Local Development

To test a plugin locally without installing it from the marketplace:

```bash
claude --plugin-dir ./pdca
claude --plugin-dir ./gemini-media
```

The `gemini-media` scripts also run standalone:

```bash
# Image generation
python3 gemini-media/skills/generate-image/scripts/generate_image.py generate \
  --prompt "a steampunk cityscape" \
  --output-dir "./generated-images"

# Video generation
python3 gemini-media/skills/generate-video/scripts/generate_video.py generate \
  --prompt "a camera flies through a steampunk city" \
  --output-dir "./generated-videos"
```

## License

MIT
