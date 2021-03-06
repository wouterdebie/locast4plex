import unittest

from mock import MagicMock, patch

from locast2dvr.multiplexer import Multiplexer, _remap
from locast2dvr.utils import Configuration


def create_multiplexer(config=MagicMock(),  port=6077, ssdp=MagicMock()):
    return Multiplexer(config, port, ssdp)


class TestMultiPlexer(unittest.TestCase):
    def setUp(self) -> None:
        self.config = Configuration({
            'verbose': 0,
            'logfile': None,
            'bind_address': '1.2.3.4',
            'uid': "TEST",
            'remap': False,
            'uid': '2721c2f0-6f2a-11eb-8001-acde48001122',
        })

    def test_multiplexer(self):
        port = 6077
        ssdp = MagicMock()

        mp = create_multiplexer(self.config, port, ssdp)

        self.assertEqual(mp.port, port)
        self.assertEqual(mp.config, self.config)
        self.assertEqual(mp.tuners, [])
        self.assertEqual(mp.city, "Multiplexer")
        self.assertEqual(mp.uid, "2721c2f0-6f2a-11eb-8001-acde48001122")
        self.assertEqual(mp.ssdp, ssdp)
        self.assertEqual(mp.url, "http://1.2.3.4:6077")

    def test_start(self):
        port = 6077
        ssdp = MagicMock()

        with patch("locast2dvr.multiplexer.start_http") as http:
            mp = create_multiplexer(self.config, port, ssdp)
            mp.log = MagicMock()
            mp.start()
            http.assert_called_once_with(
                self.config, port, "2721c2f0-6f2a-11eb-8001-acde48001122", mp, ssdp, mp.log
            )
            mp.log.info.assert_called_once_with(f"Started at {mp.url}")

    def test_start_with_remap(self):
        port = 6077
        ssdp = MagicMock()
        self.config.remap = True

        with patch("locast2dvr.multiplexer.start_http") as http:
            mp = create_multiplexer(self.config, port, ssdp)
            mp.log = MagicMock()
            mp.start()

            mp.log.warn.assert_called_once()

    def test_register(self):
        tuner1 = MagicMock()
        tuner2 = MagicMock()
        tuners = [tuner1, tuner2]
        mp = create_multiplexer(self.config, 6077, MagicMock())
        mp.log = MagicMock()
        mp.register(tuners)

        self.assertEqual(len(mp.tuners), 2)
        self.assertEqual(mp.log.info.call_count, 2)

    def test_get_stations(self):
        tuner1 = MagicMock()
        locast_service1 = MagicMock()
        tuner1.locast_service = locast_service1
        locast_service1.get_stations.return_value = [{
            "id": 1
        }]

        tuner2 = MagicMock()
        locast_service2 = MagicMock()
        tuner2.locast_service = locast_service2
        locast_service2.get_stations.return_value = [{
            "id": 2
        }]

        mp = create_multiplexer(self.config, 6077, MagicMock())
        mp.tuners = [tuner1, tuner2]

        stations = mp.get_stations()

        expected_service_mapping = {
            "1": locast_service1,
            "2": locast_service2
        }
        self.assertEqual(mp.station_service_mapping, expected_service_mapping)

        expected_stations = [{"id": 1}, {"id": 2}]
        self.assertEqual(stations, expected_stations)

    @patch('locast2dvr.multiplexer._remap')
    def test_get_stations_remap(self, remap: MagicMock()):
        remap.return_value = ("foo", "bar")

        tuner1 = MagicMock()
        locast_service1 = MagicMock()
        tuner1.locast_service = locast_service1
        station = MagicMock()
        station.return_value = {
            "id": 1
        }
        locast_service1.get_stations.return_value = [station]
        self.config.remap = True

        mp = create_multiplexer(self.config, 6077, MagicMock())
        mp.tuners = [tuner1]
        stations = mp.get_stations()

        remap.assert_called_with(station, 0)

    def test_get_station_stream_uri(self):
        mp = create_multiplexer(self.config, 6077, MagicMock())

        tuner1 = MagicMock()
        locast_service1 = MagicMock()
        mp.station_service_mapping = {
            "1": locast_service1
        }
        mp.tuners = [tuner1]
        mp.get_stations = MagicMock()
        mp.get_station_stream_uri("1")
        locast_service1.get_station_stream_uri.assert_called_with("1")

    def test_remap(self):
        station1 = {"channel": "1", "callSign": "CBS 1"}
        station2 = {"channel": "2.2", "callSign": "CBS 2.2"}

        self.assertEqual(_remap(station1, 1), ("101", "CBS 101"))
        self.assertEqual(_remap(station2, 3), ("302.2", "CBS 302.2"))
