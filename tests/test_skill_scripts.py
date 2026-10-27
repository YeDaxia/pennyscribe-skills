import json
import http.client
import importlib.util
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "repurpose-podcast"


def load_acquirer():
    spec = importlib.util.spec_from_file_location("acquire_media", SKILL / "scripts" / "acquire_media.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_preview_server():
    spec = importlib.util.spec_from_file_location("serve_site", SKILL / "scripts" / "serve_site.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_transcriber():
    spec = importlib.util.spec_from_file_location("transcribe", SKILL / "scripts" / "transcribe.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillScriptTests(unittest.TestCase):
    def test_public_page_fallback_downloads_and_normalizes_once(self):
        module = load_acquirer()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "source"

            def fake_download(_url, target):
                target.write_bytes(b"original-audio")

            def fake_normalize(source, target):
                self.assertEqual(source.read_bytes(), b"original-audio")
                target.write_bytes(b"normalized-audio")

            argv = [
                "acquire_media.py",
                "https://www.xiaoyuzhoufm.com/episode/example",
                "--output-dir",
                str(output),
            ]
            failed_probe = subprocess.CompletedProcess([], 1, "", "unsupported")
            with (
                mock.patch.object(module.shutil, "which", return_value="/usr/bin/tool"),
                mock.patch.object(module, "run", return_value=failed_probe),
                mock.patch.object(module, "apple_episode", return_value=(None, {})),
                mock.patch.object(module, "page_media", return_value=("https://cdn.example.com/episode.mp3", {"title": "Episode"})),
                mock.patch.object(module, "download", side_effect=fake_download) as downloader,
                mock.patch.object(module, "normalize", side_effect=fake_normalize) as normalizer,
                mock.patch.object(sys, "argv", argv),
            ):
                self.assertEqual(module.main(), 0)

            downloader.assert_called_once()
            normalizer.assert_called_once()
            self.assertEqual((output / "media.mp3").read_bytes(), b"normalized-audio")
            self.assertFalse((output / "download.mp3").exists())
            metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["platform"], "xiaoyuzhou")
            self.assertEqual(metadata["title"], "Episode")

    def test_resolves_apple_episode_with_public_lookup_metadata(self):
        module = load_acquirer()
        payload = {"results": [{"trackId": 456, "episodeUrl": "https://cdn.example.com/episode.mp3", "trackName": "Episode", "collectionName": "Show", "trackTimeMillis": 123000}]}
        response = subprocess.CompletedProcess([], 0, json.dumps(payload).encode(), b"")
        with mock.patch.object(module.subprocess, "run", return_value=response):
            media, metadata = module.apple_episode("https://podcasts.apple.com/us/podcast/example/id123?i=456")
        self.assertEqual(media, "https://cdn.example.com/episode.mp3")
        self.assertEqual(metadata["creator"], "Show")
        self.assertEqual(metadata["duration_seconds"], 123)

    def test_prefers_source_language_manual_youtube_subtitles_without_audio(self):
        module = load_acquirer()
        info = {
            "webpage_url": "https://www.youtube.com/watch?v=example",
            "extractor_key": "Youtube",
            "title": "有人工字幕的视频",
            "channel": "Example Channel",
            "language": "zh-Hans",
            "subtitles": {
                "zh-Hans": [{"ext": "json3", "url": "https://captions.example/manual?lang=zh-Hans"}],
                "en": [{"ext": "json3", "url": "https://captions.example/manual?lang=zh-Hans&tlang=en"}],
            },
            "automatic_captions": {
                "zh": [{"ext": "json3", "url": "https://captions.example/auto?lang=zh"}],
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "source"

            def fake_download(url, target):
                self.assertEqual(url, "https://captions.example/manual?lang=zh-Hans")
                target.write_text(json.dumps({"events": [{"segs": [{"utf8": "第一句人工字幕。"}]}, {"segs": [{"utf8": "第二句人工字幕。"}]}]}), encoding="utf-8")

            argv = ["acquire_media.py", info["webpage_url"], "--output-dir", str(output)]
            probe = subprocess.CompletedProcess([], 0, json.dumps(info), "")
            with (
                mock.patch.object(module.shutil, "which", return_value="/usr/bin/tool"),
                mock.patch.object(module, "run", return_value=probe) as runner,
                mock.patch.object(module, "download", side_effect=fake_download),
                mock.patch.object(module, "normalize") as normalizer,
                mock.patch.object(sys, "argv", argv),
            ):
                self.assertEqual(module.main(), 0)

            runner.assert_called_once()
            normalizer.assert_not_called()
            self.assertFalse((output / "media.mp3").exists())
            self.assertEqual((output / "transcript.txt").read_text(encoding="utf-8"), "第一句人工字幕。\n第二句人工字幕。\n")
            metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["transcript_source"], "youtube-manual-subtitles")
            self.assertEqual(metadata["transcript_language"], "zh-Hans")

    def test_uses_source_language_auto_caption_and_rejects_translations(self):
        module = load_acquirer()
        selected = module.choose_youtube_caption({
            "language": "ja",
            "subtitles": {
                "en": [{"ext": "json3", "url": "https://captions.example/manual?lang=ja&tlang=en"}],
            },
            "automatic_captions": {
                "ja-orig": [{"ext": "json3", "url": "https://captions.example/auto?lang=ja"}],
                "zh-Hans": [{"ext": "json3", "url": "https://captions.example/auto?lang=ja&tlang=zh-Hans"}],
            },
        })
        self.assertIsNotNone(selected)
        self.assertEqual(selected["kind"], "automatic")
        self.assertEqual(selected["language"], "ja-orig")
        self.assertNotIn("tlang", selected["format"]["url"])

    def test_uses_default_manual_track_when_youtube_omits_language(self):
        module = load_acquirer()
        selected = module.choose_youtube_caption({
            "language": None,
            "subtitles": {
                "en": [{"ext": "json3", "url": "https://captions.example/manual?lang=en"}],
                "de": [{"ext": "json3", "url": "https://captions.example/manual?lang=de"}],
            },
            "automatic_captions": {},
        })
        self.assertIsNotNone(selected)
        self.assertEqual(selected["kind"], "manual")
        self.assertEqual(selected["language"], "en")

    def test_initializes_project_from_youtube_subtitles_without_api_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transcript = root / "transcript.txt"
            metadata = root / "metadata.json"
            output = root / "project.json"
            transcript.write_text("原语言字幕第一段。\n原语言字幕第二段。\n", encoding="utf-8")
            metadata.write_text(json.dumps({
                "source_url": "https://www.youtube.com/watch?v=example",
                "platform": "youtube",
                "title": "字幕视频",
                "creator": "Example Channel",
                "transcript_source": "youtube-automatic-subtitles",
                "transcript_language": "zh-Hans",
            }, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([
                sys.executable, str(SKILL / "scripts" / "transcribe.py"),
                "--transcript", str(transcript), "--metadata", str(metadata), "--output", str(output),
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            project = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(project["transcript"]["raw"], "原语言字幕第一段。\n原语言字幕第二段。")
            self.assertEqual(project["transcript"]["source"], "youtube-automatic-subtitles")
            self.assertEqual(project["transcript"]["language"], "zh-Hans")
            self.assertEqual(project["xiaohongshu"]["theme"], "visual-accessibility")
            self.assertNotIn("pennyscribe", project)

    def test_transcribes_with_elevenlabs_using_unified_api_key_variable(self):
        module = load_transcriber()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "media.mp3"
            metadata = root / "metadata.json"
            output = root / "project.json"
            audio.write_bytes(b"audio")
            metadata.write_text(json.dumps({"source_url": "https://example.com", "platform": "test", "title": "Episode"}), encoding="utf-8")
            response = {"text": "ElevenLabs 转写正文。", "language_code": "zh", "language_probability": 0.99}
            completed = subprocess.CompletedProcess([], 0, json.dumps(response), "")
            argv = [
                "transcribe.py", str(audio), "--metadata", str(metadata), "--output", str(output),
                "--provider", "elevenlabs", "--language-code", "zh", "--diarize",
            ]
            with (
                mock.patch.object(module.subprocess, "run", return_value=completed) as runner,
                mock.patch.dict(module.os.environ, {"PENNYSCRIBE_API_KEY": "secret-elevenlabs-key"}, clear=True),
                mock.patch.object(sys, "argv", argv),
            ):
                self.assertEqual(module.main(), 0)

            curl_config = runner.call_args.kwargs["input"]
            self.assertIn('header = "xi-api-key: secret-elevenlabs-key"', curl_config)
            self.assertIn('form = "model_id=scribe_v2"', curl_config)
            self.assertIn('form = "language_code=zh"', curl_config)
            self.assertIn('form = "diarize=true"', curl_config)
            project = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(project["transcript"]["raw"], "ElevenLabs 转写正文。")
            self.assertEqual(project["transcript"]["source"], "elevenlabs")
            self.assertEqual(project["transcription"]["provider"], "elevenlabs")
            self.assertNotIn("pennyscribe", project)

    def test_builds_self_contained_workspace_with_five_views(self):
        project = {
            "schema_version": 1,
            "source": {"url": "https://example.com/episode", "platform": "test", "title": "A useful conversation", "creator": "Example Show", "cover": None},
            "transcript": {"raw": "第一段完整内容。第二段完整内容。", "readable": {"title": "整理后的全文", "dek": "导语", "sections": [{"id": "section-01", "heading": "开始", "paragraphs": [{"id": "p-001", "text": "第一段完整内容。", "source_start": 0, "source_end": 8}]}]}},
            "digest": {"recommendation": "值得阅读", "summary": "摘要", "insights": [{"text": "观点", "source_paragraph_ids": ["p-001"]}], "quotes": [{"text": f"金句 {index}", "fidelity": "verbatim", "source_paragraph_ids": ["p-001"]} for index in range(1, 4)], "audience": ["创作者"]},
            "x": {"single_posts": [{"text": "一条 X https://example.com/episode", "source_paragraph_ids": ["p-001"]}], "threads": []},
            "xiaohongshu": {"title_options": ["更适合传播的新标题"], "caption": "第一段发布文案。\n\n第二段发布文案。", "theme": "layout-magazine", "cards": [{"kind": "cover" if index == 1 else "insight", "eyebrow": "PODCAST NOTES", "title": f"卡片标题 {index}", "body": "封面钩子" if index == 1 else "先用第一段明确说出这张内容卡最值得记住的核心结论，让读者立即理解主题。\n\n第二段补充来自播客全文的关键事实、必要背景和具体例子，让这个判断拥有可靠依据。\n\n第三段进一步解释这件事带来的影响、现实张力或仍待回答的问题，让卡片能够独立成立。", "source_paragraph_ids": ["p-001"]} for index in range(1, 5)]},
        }
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "project.json"
            target = Path(directory) / "index.html"
            source.write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run([sys.executable, str(SKILL / "scripts" / "build_workspace.py"), str(source), "--output", str(target)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            html = target.read_text(encoding="utf-8")
            for text in ("PennyScribe Skills", "导读与摘要", "金句", "阅读全文", "X 素材", "小红书素材", "标题与文案", "卡片编辑", "第一段完整内容。", "卡片标题", "导出全部卡片", "复制文字", "复制卡片", "自由排版", "重置排版", "隐藏页码", "当前内容块", "文字颜色", "重置此块", "data-layout-key", "data-typography-key", "function bindTypographyInteractions", "function bindLayoutInteractions", "function headlineClass", "function zipFiles", "ClipboardItem"):
                self.assertIn(text, html)
            self.assertLess(html.index("导读与摘要"), html.index("小红书素材"))
            self.assertIn('class="view active" id="view-xhs"', html)
            self.assertIn('class="xhs-pane active" id="xhs-pane-cards"', html)
            self.assertIn('aria-label="在 GitHub 查看 PennyScribe Skills"', html)
            self.assertIn('href="https://github.com/YeDaxia/pennyscribe-skills"', html)
            self.assertIn('class="card-style-tools" aria-label="卡片字体设置"', html)
            self.assertIn('type="range" min="24" max="76"', html)
            self.assertIn('.cards.layout-mode .card-style-tools{display:grid', html)
            self.assertIn("typography[`${key}_color`]", html)
            for theme in ("手绘涂鸦", "新粗野主义", "剪纸风格", "中世纪现代", "无障碍设计", "漫画书", "包豪斯", "杂志排版", "复古未来主义", "扁平风格", "白底栏目笔记", "瑞士国际主义"):
                self.assertIn(theme, html)
            for css in ("theme-visual-neo-brutalism:before{left:auto", "theme-visual-paper-cutout:after{content:none}", "theme-retro-mid-century:before{left:auto", "Centered composition pass", "Natural headline flow", "text-wrap:pretty", "theme-visual-hand-drawn:before{bottom:auto;width:auto}", "theme-visual-accessibility.card-cover:after{left:auto", "theme-visual-comic-book:before{left:auto", "theme-retro-bauhaus:before{left:auto", "theme-layout-magazine.card-cover .body{max-width:100%", "theme-retro-futurism:before{left:48px", "theme-core-flat-design:before{left:auto", "text-wrap:balance", "theme-white-collage .body p:before", "theme-international-grid.card-cover .body p:after"):
                self.assertIn(css, html)
            for removed_badge in ('content:"BIG\\A IDEA"', 'content:"SIDE\\A NOTE"', 'content:"PAPER\\A NOTE"', 'content:"KEY\\A POINT"', 'content:"SIGNAL\\A 01"'):
                self.assertNotIn(removed_badge, html)
            self.assertIn("function cardParagraphs", html)
            self.assertNotIn("__PROJECT_DATA__", html)

            validation = subprocess.run([sys.executable, str(SKILL / "scripts" / "validate_project.py"), str(source)], capture_output=True, text=True)
            self.assertEqual(validation.returncode, 0, validation.stderr)

            invalid = json.loads(json.dumps(project, ensure_ascii=False))
            invalid["xiaohongshu"]["cards"][1]["body"] = "第一段保留足够多的具体信息，用于验证失败原因来自段落数量而不是正文长度。\n\n第二段同样写得足够完整，但整张卡仍然只有两个段落，因此必须被三段式规则拒绝。"
            source.write_text(json.dumps(invalid, ensure_ascii=False), encoding="utf-8")
            validation = subprocess.run([sys.executable, str(SKILL / "scripts" / "validate_project.py"), str(source)], capture_output=True, text=True)
            self.assertEqual(validation.returncode, 2)
            self.assertIn("must contain exactly 3 body paragraphs", validation.stderr)

    def test_builds_switchable_local_library(self):
        def project(number):
            return {
                "schema_version": 1,
                "source": {"url": f"https://example.com/episode-{number}", "platform": "test", "title": f"Episode {number}", "creator": "Example Show", "cover": None},
                "transcript": {"raw": "完整内容。", "readable": {"title": f"Readable {number}", "dek": "导语", "sections": []}},
                "digest": {"recommendation": "值得阅读", "summary": "摘要", "insights": [], "quotes": [], "audience": []},
                "x": {"single_posts": [], "threads": []},
                "xiaohongshu": {"title_options": [], "caption": "", "theme": "layout-magazine", "cards": []},
            }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = []
            for number in (1, 2):
                path = root / f"project-{number}.json"
                path.write_text(json.dumps(project(number), ensure_ascii=False), encoding="utf-8")
                sources.append(path)
            output = root / "library"
            result = subprocess.run([sys.executable, str(SKILL / "scripts" / "build_site.py"), *(str(path) for path in sources), "--output-dir", str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            index = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("切换播客", index)
            self.assertIn("在 GitHub 获取 Skill", index)
            self.assertIn('href="https://github.com/YeDaxia/pennyscribe-skills"', index)
            self.assertIn("Episode 1", index)
            self.assertIn("Episode 2", index)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest), 2)
            for item in manifest:
                self.assertTrue((output / item["file"]).exists())

    def test_serves_generated_library_on_loopback(self):
        module = load_preview_server()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text("<h1>Podcast Library</h1>", encoding="utf-8")
            server = module.make_server(root, "127.0.0.1", 0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                port = server.server_address[1]
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
                connection.request("GET", "/")
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertIn(b"Podcast Library", response.read())
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                connection.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)

    def test_acquires_and_normalizes_local_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.wav"
            output = Path(directory) / "source"
            generated = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.2", str(source)], capture_output=True, text=True)
            self.assertEqual(generated.returncode, 0, generated.stderr)
            result = subprocess.run([sys.executable, str(SKILL / "scripts" / "acquire_media.py"), str(source), "--output-dir", str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertGreater((output / "media.mp3").stat().st_size, 0)
            metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["platform"], "local-file")


if __name__ == "__main__":
    unittest.main()
