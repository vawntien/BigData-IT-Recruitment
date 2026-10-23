"""Authorized loopback-only aggregate initialization, isolated to each session.

The ignored configuration enables only this machine. Every new session runs the
original receivers. Navigation checks source bytes but reuses validated results
when the same package is intact. No global result cache or producer execution.
"""
from hashlib import sha256
import json
from pathlib import Path

from . import q01_real_preview as q01
from . import technical_preview as technical

QUERIES = ('Q01', 'Q02', 'Q03', 'Q04', 'Q06', 'Q08')
CONFIG_PATH = Path(__file__).resolve().parents[1] / 'local_preview.json'
AUTHORIZATION = 'TV1_LOCAL_DEMO_20261023'
STATE_KEY = '_local_real_sources'


def filename(query):
    return ('TV2_Q06_OFFICIAL_20261022_01.zip' if query == 'Q06'
            else f'TV2_{query}_VALIDATED_HANDOFF_TV3_20261022.zip')


def expected_hash(query):
    return q01.EXPECTED_SHA256 if query == 'Q01' else technical.PINS[query]['sha256']


def read_config():
    try:
        return json.loads(CONFIG_PATH.read_text(encoding='utf8'))
    except (OSError, ValueError):
        return {}


def configuration_allowed(config, address):
    return (address == '127.0.0.1' and isinstance(config, dict)
            and set(config) == {'enabled', 'authorization', 'source_root'}
            and config.get('enabled') is True
            and config.get('authorization') == AUTHORIZATION
            and isinstance(config.get('source_root'), str)
            and not config['source_root'].startswith(('\\\\', '//'))
            and Path(config['source_root']).is_absolute())


def discover(query, root):
    """Only two approved handoff locations per query, never arbitrary scanning."""
    root = Path(root).resolve()
    candidates = (root / filename(query), root / f'TV2_HANDOFF_TV3_{query}' / filename(query))
    issue = 'MISSING_PACKAGE'
    for path in candidates:
        try:
            if not path.is_file():
                continue
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                issue = 'INVALID_LOCAL_PATH'
                continue
            if path.stat().st_size > technical.MAX_BYTES:
                issue = 'ARCHIVE_TOO_LARGE'
                continue
            with path.open('rb') as stream:
                data = stream.read(technical.MAX_BYTES + 1)
            if len(data) > technical.MAX_BYTES:
                issue = 'ARCHIVE_TOO_LARGE'
                continue
            digest = sha256(data).hexdigest()
            if digest == expected_hash(query):
                return path, digest, ''
            issue = 'ARCHIVE_HASH_MISMATCH'
        except OSError:
            issue = 'UNREADABLE_PACKAGE'
    return None, None, issue


def synchronize(state, config, address, progress=None):
    """Mutable state belongs to caller/session; ERROR entries contain no result."""
    if not configuration_allowed(config, address):
        state.clear()
        state.update({q: {'status': 'ERROR', 'issue': 'LOCAL_DEMO_NOT_ENABLED'} for q in QUERIES})
        return state
    for index, query in enumerate(QUERIES):
        if progress:
            progress(index, query)
        path, digest, issue = discover(query, config['source_root'])
        previous = state.get(query, {})
        if issue:
            state[query] = {'status': 'ERROR', 'issue': issue}
            continue
        identity = (str(path), digest)
        if previous.get('identity') == identity and previous.get('status') == 'READY':
            continue
        # Discard first: a failed reload can never leave stale chart data.
        state[query] = {'status': 'ERROR', 'issue': 'VALIDATING'}
        try:
            result = (q01.load_q01_preview(str(path), confirmed=True) if query == 'Q01'
                      else technical.load_preview(query, str(path), confirmed=True))
            if result.passed:
                state[query] = {'status': 'READY', 'issue': '', 'identity': identity, 'result': result}
            else:
                state[query] = {'status': 'ERROR', 'issue': result.issue}
        except Exception:
            state[query] = {'status': 'ERROR', 'issue': 'VALIDATION_FAILED'}
    return state


def initialize_session():
    import streamlit as st
    state = st.session_state.setdefault(STATE_KEY, {})
    config = read_config()
    address = st.get_option('server.address')
    with st.spinner('Xác minh sáu nguồn dữ liệu thật…'):
        synchronize(state, config, address)
    st.session_state[STATE_KEY] = state


def current_result(query):
    import streamlit as st
    entry = st.session_state.get(STATE_KEY, {}).get(query, {})
    if entry.get('status') != 'READY':
        st.error(query + ' không khả dụng · ' + entry.get('issue', 'LOCAL_DEMO_NOT_ENABLED'))
        st.caption('Khôi phục gói nguồn hoặc cấu hình local rồi thử lại. Không có dữ liệu thay thế.')
        if st.button('Thử xác minh lại', key='retry_' + query):
            st.rerun()
        return None
    return entry['result']
