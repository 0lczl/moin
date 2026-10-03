"""Behavior tests for the durable live room state boundary."""
import json

import pytest

from moin_studio.live_room import (
    ActiveRoomExists,
    InvalidManagementSecret,
    ListenerNotFound,
    RoomEnded,
    RoomFull,
    RoomNotFound,
    RoomStore,
)


def test_room_capability_and_events_survive_restart_without_storing_secret(tmp_path):
    store = RoomStore(tmp_path)
    room, secret = store.create_room('Friday prayer', 'en', now=100)

    assert len(room['id']) >= 24
    assert len(secret.encode()) >= 32
    assert room['name'] == 'Friday prayer'
    assert room['language'] == 'en'
    assert room['status'] == 'active'
    assert 'management_secret' not in room
    disk = (tmp_path / 'live-room.json').read_text()
    assert secret not in disk
    with pytest.raises(InvalidManagementSecret):
        store.events(room['id'], now=100)

    listener = store.join(room['id'], now=101)
    assert len(listener) >= 32
    assert listener not in (tmp_path / 'live-room.json').read_text()
    joined = store.events(room['id'], after=1, limit=1, listener_id=listener, now=101)[0]
    assert 'listener_id' not in joined
    assert 'listeners' not in store.state(room['id'], now=101)
    segment_event = store.append_segment(
        room['id'], secret, {'text': 'Welcome', 'language': 'en'}, now=102,
    )
    assert segment_event['seq'] == 3

    restarted = RoomStore(tmp_path)
    assert restarted.state(room['id'], now=103)['listener_count'] == 1
    assert [event['seq'] for event in restarted.events(room['id'], admin_secret=secret, now=103)] == [1, 2, 3]
    assert restarted.events(room['id'], after=2, admin_secret=secret, now=103) == [segment_event]


def test_one_active_room_listener_limit_and_ordered_join_leave_events(tmp_path):
    store = RoomStore(tmp_path, max_listeners=2)
    room, secret = store.create_room('Room', 'fr', now=10)
    with pytest.raises(ActiveRoomExists):
        store.create_room('Second room', 'en', now=11)

    one = store.join(room['id'], now=12)
    two = store.join(room['id'], now=13)
    with pytest.raises(RoomFull):
        store.join(room['id'], now=14)
    store.leave(room['id'], one, now=15)
    three = store.join(room['id'], now=16)
    with pytest.raises(ListenerNotFound):
        store.leave(room['id'], 'missing', now=17)

    events = store.events(room['id'], admin_secret=secret, now=18)
    assert [event['seq'] for event in events] == [1, 2, 3, 4, 5]
    assert [event['type'] for event in events] == [
        'room_created', 'listener_joined', 'listener_joined',
        'listener_left', 'listener_joined',
    ]
    assert store.state(room['id'], now=18)['listener_count'] == 2
    assert 'listeners' not in store.state(room['id'], now=18)
    assert one not in json.dumps(events)
    assert two not in json.dumps(events)
    assert three not in json.dumps(events)


def test_management_capability_guards_segment_and_end(tmp_path):
    store = RoomStore(tmp_path)
    room, secret = store.create_room('Room', 'en', now=1)
    listener = store.join(room['id'], now=1.5)
    assert store.authorize_admin(room['id'], secret, now=1.5) is True
    assert store.authorize_listener(room['id'], listener, now=1.5) is True
    with pytest.raises(InvalidManagementSecret):
        store.append_segment(room['id'], 'wrong', {'text': 'private'}, now=2)
    with pytest.raises(InvalidManagementSecret):
        store.end(room['id'], 'wrong', now=2)

    ended = store.end(room['id'], secret, now=3)
    assert ended['active'] is False
    assert ended['status'] == 'ended'
    assert ended['ended_at'] == 3
    with pytest.raises(RoomEnded):
        store.join(room['id'], now=4)
    with pytest.raises(RoomEnded):
        store.append_segment(room['id'], secret, {'text': 'late'}, now=4)
    with pytest.raises(RoomEnded):
        store.authorize_listener(room['id'], listener, now=4)
    with pytest.raises(RoomEnded):
        store.events(room['id'], listener_id=listener, now=4)
    assert [event['type'] for event in store.events(room['id'], admin_secret=secret, now=4)] == [
        'room_created', 'listener_joined', 'room_ended',
    ]

    replacement, _ = store.create_room('Replacement', 'fr', now=5)
    assert replacement['id'] != room['id']
    assert store.state(room['id'], now=6)['status'] == 'ended'
    assert [event['type'] for event in store.events(room['id'], admin_secret=secret, now=6)] == [
        'room_created', 'listener_joined', 'room_ended',
    ]
    restarted = RoomStore(tmp_path)
    assert restarted.state(room['id'], now=6)['status'] == 'ended'


def test_expiry_cleanup_removes_room_and_creation_reaps_old_room(tmp_path):
    store = RoomStore(tmp_path, ttl_seconds=10)
    room, _ = store.create_room('Room', 'en', now=20)

    assert store.cleanup(now=29) is False
    assert store.cleanup(now=30) is True
    with pytest.raises(RoomNotFound):
        store.state(room['id'], now=30)
    assert json.loads((tmp_path / 'live-room.json').read_text())['rooms'] == {}

    old, _ = store.create_room('Old', 'en', now=40)
    newer, _ = store.create_room('New', 'fr', now=50)
    assert old['id'] != newer['id']


def test_active_room_lease_ends_abandoned_room_and_keeps_its_history(tmp_path):
    store = RoomStore(tmp_path, ttl_seconds=20, max_active_seconds=5)
    room, secret = store.create_room('Abandoned', 'en', now=100)
    listener = store.join(room['id'], now=101)

    ended = store.state(now=105)
    assert ended['id'] == room['id']
    assert ended['status'] == 'ended'
    assert ended['ended_at'] == 105
    assert store.authorize_admin(room['id'], secret, now=105) is True
    with pytest.raises(RoomEnded):
        store.authorize_listener(room['id'], listener, now=105)
    lease_events = store.events(
        room['id'], admin_secret=secret, now=105,
    )
    assert [event['type'] for event in lease_events] == [
        'room_created', 'listener_joined', 'room_ended',
    ]
    assert lease_events[-1]['reason'] == 'lease_expired'

    replacement, _ = store.create_room('Replacement', 'fr', now=105)
    assert replacement['id'] != room['id']
    assert store.state(room['id'], now=106)['status'] == 'ended'
    assert store.cleanup(now=120) is True
    with pytest.raises(RoomNotFound):
        store.state(room['id'], now=120)


def test_default_room_accepts_fifty_listeners_and_rejects_next(tmp_path):
    store = RoomStore(tmp_path)
    room, _ = store.create_room('Friday lesson', 'en')
    listeners = [store.join(room['id']) for _ in range(50)]
    assert len(set(listeners)) == 50
    assert store.state(room['id'])['listener_count'] == 50
    with pytest.raises(RoomFull):
        store.join(room['id'])
