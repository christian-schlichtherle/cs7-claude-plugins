# cs7-claude-plugins

A [Claude Code](https://claude.ai/code) plugin marketplace providing AI-powered image and video generation using Google's Gemini API.

## Plugins

### gemini-media

Generate and edit images and videos directly from Claude Code using Google's Gemini models — commonly known as **Nano Banana** (image generation) and **Veo** (video generation).

**Skills:**

| Skill | Trigger | Models |
|---|---|---|
| `generate-image` | "generate an image", "edit this image", "refine the image" | Nano Banana (Gemini 3.1 Flash, Gemini 3 Pro, Gemini 2.5 Flash) |
| `generate-video` | "generate a video", "animate this image", "extend the video" | Veo 3.1, Veo 3.0 |

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

### Prerequisites

- [Claude Code](https://claude.ai/code) v1.0.33+
- Python 3.7+ (scripts use only stdlib — no pip install needed)
- A [Gemini API Key](https://aistudio.google.com/api-keys) from Google's AI Studio

### Add the marketplace

```bash
claude plugin marketplace add christian-schlichtherle/cs7-claude-plugins
```

### Install the plugin

```bash
claude plugin install gemini-media@cs7-claude-plugins
```

### Set your API key

```bash
export GEMINI_API_KEY='your-key-here'
```

Or create a `.env` file in the directory where you run Claude Code:

```
GEMINI_API_KEY=your-key-here
```

## Usage

Once installed, the skills activate automatically when you ask Claude Code to generate media:

```
> Generate an image of a steampunk cityscape at sunset in 16:9

> Edit the image — add a dirigible in the sky

> Generate a video of a camera slowly flying through the city
```

The skills handle model selection, prompt optimization, and output management. Generated files are saved to `./generated-images/` and `./generated-videos/` in your working directory and auto-opened on macOS.

## Local Development

To test the plugin locally without installing from a marketplace:

```bash
claude --plugin-dir ./gemini-media
```

Or run the scripts directly:

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
