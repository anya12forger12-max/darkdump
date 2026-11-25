"""Regression tests for untrusted scrape data and unauthenticated web routes."""

import importlib.util
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from darkdump import Darkdump, get_validated, is_safe_scrape_url

ROOT = Path(__file__).resolve().parents[1]


def _load_web_app():
    spec = importlib.util.spec_from_file_location(
        'darkdump_web_app', ROOT / 'darkdump-web' / 'app.py'
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gallery_escapes_hostile_image_sources(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = Path(Darkdump().generate_html(
        [
            '1" onerror="alert(1)',
            'javascript:alert(1)',
            'https://example.test/image.png',
        ],
        'https://example.test/',
    ))
    text = path.read_text(encoding='utf-8')

    assert 'onerror="alert(1)"' not in text
    assert '&quot;' in text
    assert 'javascript:' not in text
    assert 'src="https://example.test/image.png"' in text


def test_gallery_refuses_to_follow_output_symlink(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    dd = Darkdump()
    output_dir = tmp_path / 'dd_scrape_image_dump'
    output_dir.mkdir()
    target = tmp_path / 'victim.txt'
    target.write_text('do not overwrite', encoding='utf-8')
    link = output_dir / (dd.sanitize_filename('https://example.test') + '.html')
    link.symlink_to(target)

    with pytest.raises(OSError):
        dd.generate_html(['https://example.test/a.png'], 'https://example.test')
    assert target.read_text(encoding='utf-8') == 'do not overwrite'


def test_scrape_url_dns_validation():
    loopback = [(None, None, None, '', ('127.0.0.1', 80))]
    with patch('darkdump.socket.getaddrinfo', return_value=loopback):
        assert is_safe_scrape_url('http://public-looking.test/internal') is False
    assert is_safe_scrape_url('http://localhost/admin') is False
    assert is_safe_scrape_url('http://metadata.google.internal/creds') is False
    assert is_safe_scrape_url('file:///etc/passwd') is False
    assert is_safe_scrape_url('http://example.onion/', allow_onion=False) is False
    assert is_safe_scrape_url('http://example.onion/', allow_onion=True) is True


def test_redirect_targets_are_revalidated():
    redirect = MagicMock(status_code=302, headers={'Location': 'http://127.0.0.1/admin'})

    def resolve(host, port, **_kwargs):
        address = '93.184.216.34' if host == 'example.test' else '127.0.0.1'
        return [(None, None, None, '', (address, port))]

    with (
        patch('darkdump.socket.getaddrinfo', side_effect=resolve),
        patch('darkdump.requests.get', return_value=redirect) as get,
    ):
        with pytest.raises(ValueError, match='unsafe URL'):
            get_validated(
                'https://example.test/page',
                headers={},
                proxies={},
                timeout=1,
            )
    get.assert_called_once()


def test_web_app_limits_concurrency_and_export_size():
    web = _load_web_app()
    assert 0 < web.app.config['MAX_CONTENT_LENGTH'] <= 2 * 1024 * 1024

    client = web.app.test_client()
    assert client.post('/export', data='[]', content_type='text/plain').status_code == 400

    old_slots = web._scan_slots
    web._scan_slots = threading.BoundedSemaphore(1)
    try:
        web._scan_slots.acquire(blocking=False)
        response = client.get('/search?q=test')
        assert response.status_code == 200
        assert b'Too many concurrent scans' in response.data
    finally:
        web._scan_slots = old_slots
