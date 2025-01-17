import unittest
from unittest.mock import patch, AsyncMock
from datetime import datetime
from bot_staty import fetch_player_data

class TestFetchPlayerData(unittest.TestCase):

    @patch('bot_staty.get_data', new_callable=AsyncMock)
    async def test_fetch_player_data(self, mock_get_data):
        # Mock the API responses
        mock_get_data.side_effect = [
            {
                "data": [
                    {
                        "player_name": "Test Player",
                        "player_key": "12345",
                        "rank": 1,
                        "stat": 100
                    }
                ]
            },
            {
                "data": [
                    {
                        "player_name": "Test Player",
                        "stat": 50
                    }
                ]
            }
        ]

        date_from = "2023-01-01"
        date_to = "2023-12-31"
        player_name = "Test Player"

        player_data = await fetch_player_data(player_name, date_from, date_to)

        self.assertIsNotNone(player_data)
        self.assertEqual(player_data['player_name'], "Test Player")
        self.assertEqual(player_data['rank'], 1)
        self.assertEqual(player_data['maximums'], 100)
        self.assertEqual(player_data['average'], 50)

if __name__ == '__main__':
    unittest.main()
