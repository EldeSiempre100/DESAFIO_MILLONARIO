from __future__ import annotations

from fastapi.testclient import TestClient

from desafio_online.app import app


def test_host_loads_phase4_audio_policy_after_host_script() -> None:
    with TestClient(app) as client:
        html = client.get("/host/123456").text
        assert "/assets/sound.js?r=20260818-5" in html
        assert "/assets/host.js?r=20260818-3" in html
        assert "/assets/phase4_audio.js?r=20260818-1" in html
        assert html.index("/assets/host.js") < html.index("/assets/phase4_audio.js")


def test_host_audio_starts_automatically_without_visible_enable_button() -> None:
    with TestClient(app) as client:
        html = client.get("/host/123456").text
        host = client.get("/assets/host.js").text
        sound = client.get("/assets/sound.js").text

        assert "soundButton" not in html
        assert "Activar sonido" not in html
        assert "autoEnabled: true" in host
        assert "hostAudioStarted" in host
        assert "gameAudio.enable(backgroundForState(data.state))" in host
        assert "playbackBlocked" in sound
        assert "this.enabled = this.autoEnabled || localStorage.getItem(this.storageKey) === \"on\"" in sound


def test_game_audio_has_dedicated_question_cue_sequence() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/sound.js").text
        assert "this.cue = new Audio()" in script
        assert "beginQuestionSequence" in script
        assert "cancelQuestionSequence" in script
        assert "isQuestionSequenceActive" in script
        assert "stopVoice" in script
        assert "preloadSources" in script
        assert "QUESTION_CUE_FALLBACK_MS = 11650" in script


def test_qualifier_and_interstitial_states_keep_intro_ambient() -> None:
    with TestClient(app) as client:
        policy = client.get("/assets/phase4_audio.js").text
        for state in (
            '"lobby_open"',
            '"qualifier_open"',
            '"qualifier_results"',
            '"player_selection"',
            '"round_intro"',
            '"round_summary"',
            '"session_summary"',
        ):
            assert state in policy
        assert 'if (AMBIENT_STATES.has(state)) return "intro"' in policy


def test_question_started_plays_entry_cue_before_question_music() -> None:
    with TestClient(app) as client:
        policy = client.get("/assets/phase4_audio.js").text
        assert 'name === "question_started"' in policy
        assert "gameAudio.beginQuestionSequence" in policy
        assert 'cue: "transition"' in policy
        assert 'music: "question"' in policy
        assert "fallbackMs: QUESTION_CUE_FALLBACK_MS" in policy


def test_lifelines_overlay_question_tension_like_v3() -> None:
    with TestClient(app) as client:
        policy = client.get("/assets/phase4_audio.js").text

        fifty_block = policy.split('name === "lifeline_fifty"', 1)[1].split(
            'name === "lifeline_started"', 1
        )[0]
        assert 'gameAudio.play("lifeline")' in fifty_block
        assert "stopMusic" not in fifty_block

        timed_block = policy.split('name === "lifeline_started"', 1)[1].split(
            'name === "lifeline_finished"', 1
        )[0]
        assert 'gameAudio.play("lifeline")' in timed_block
        assert 'data.last_event.lifeline === "phone" ? "call" : "audience"' in timed_block
        assert "stopMusic" not in timed_block
        assert "cancelQuestionSequence" not in timed_block

        assert 'state === "question_active" || state === "lifeline_active"' in policy
        assert 'name === "lifeline_finished"' in policy
        assert 'gameAudio.startMusic("question")' in policy


def test_phase4_policy_does_not_use_transition_as_generic_state_effect() -> None:
    with TestClient(app) as client:
        policy = client.get("/assets/phase4_audio.js").text
        assert 'gameAudio.play("transition")' not in policy
        assert 'gameAudio.startMusic("transition")' not in policy
        assert "AMBIENT_EVENTS" in policy
        assert 'gameAudio.startMusic("intro")' in policy


def test_lifeline_buttons_do_not_prestart_question_music() -> None:
    with TestClient(app) as client:
        policy = client.get("/assets/phase4_audio.js").text
        lifeline_render = policy.split("function canonicalRenderLifelines", 1)[1].split(
            "function canonicalSyncAudio", 1
        )[0]
        assert "gameAudio.enable(null)" in lifeline_render
        assert 'gameAudio.enable("question")' not in lifeline_render
