import unittest
import discord
from unittest.mock import patch, AsyncMock
from datetime import datetime
from bot_staty import fetch_player_data, fetch_additional_stats, fill_missing_stats, create_embed

class TestFetchPlayerData(unittest.IsolatedAsyncioTestCase):

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

        player_name = "Test Player"
        date_from = "2025-01-01"
        date_to = "2025-01-10"

        player_data = await fetch_player_data(player_name, date_from, date_to)
        expected_data = [
            {
                "player_name": "Test Player",
                "player_key": "12345",
                "rank": 1,
                "stat": 100
            },
            {
                "player_name": "Test Player",
                "stat": 50
            }
        ]

        self.assertEqual(player_data, expected_data)

class TestFetchAdditionalStats(unittest.IsolatedAsyncioTestCase):

    @patch('bot_staty.get_data', new_callable=AsyncMock)
    async def test_fetch_additional_stats(self, mock_get_data):
        # Mock the API response
        mock_get_data.return_value = [
            ["Averages", "50", "60", "70"],
            ["Checkout Pcnt", "40%", "50%", "60%"]
        ]

        player_key = "12345"
        additional_stats = await fetch_additional_stats(player_key)

        self.assertIsNotNone(additional_stats)
        self.assertIn("Averages", additional_stats)
        self.assertIn("Checkout Pcnt", additional_stats)
        self.assertEqual(additional_stats["Averages"], ["50", "60", "70"])
        self.assertEqual(additional_stats["Checkout Pcnt"], ["40%", "50%", "60%"])

class TestFillMissingStats(unittest.TestCase):

    def test_fill_missing_stats(self):
        data = {
            "additional_stats": {
                "Averages": ["50", "60", "70"],
                "Checkout Pcnt": ["40%", "50%", "60%"],
                "180's per leg": ["0.2", "0.3", "0.4"]
            }
        }

        fill_missing_stats(data)

        self.assertIn("average", data)
        self.assertIn("average_actual", data)
        self.assertIn("checkout_pcnt", data)
        self.assertIn("checkout_pcnt_actual", data)
        self.assertIn("maximum_per_leg", data)
        self.assertIn("maximum_per_leg_actual", data)
        self.assertEqual(data["average"], 60.0)
        self.assertEqual(data["average_actual"], "70")
        self.assertEqual(data["checkout_pcnt"], "50.00%")
        self.assertEqual(data["checkout_pcnt_actual"], "60%")
        self.assertEqual(data["maximum_per_leg"], 0.3)
        self.assertEqual(data["maximum_per_leg_actual"], "0.4")

class TestCreateEmbed(unittest.TestCase):

    def test_create_embed(self):
        data = {
            "player_name": "Test Player",
            "rank": 1,
            "average": 60.0,
            "average_actual": "70",
            "checkout_pcnt": "50.00%",
            "checkout_pcnt_actual": "60%",
            "maximum_per_leg": 0.3,
            "maximum_per_leg_actual": "0.4",
            "maximums": 100
        }

        embed = create_embed("Test Player", data, discord.Color.blue(), "Test Description")

        self.assertEqual(embed.title, "Statistiky pro hráče Test Player")
        self.assertEqual(embed.description, "Test Description")
        self.assertEqual(embed.color, discord.Color.blue())
        self.assertEqual(embed.fields[0].name, "🏆 Rank")
        self.assertEqual(embed.fields[0].value, "1")  # Convert expected value to string
        self.assertEqual(embed.fields[1].name, "🎯 Average")
        self.assertEqual(embed.fields[1].value, "60.0 (Current: 70)")
        self.assertEqual(embed.fields[2].name, "✅ Checkout %")
        self.assertEqual(embed.fields[2].value, "50.00% (Current: 60%)")
        self.assertEqual(embed.fields[3].name, "💥 Max per Leg")
        self.assertEqual(embed.fields[3].value, "0.3 (Current: 0.4)")
        self.assertEqual(embed.fields[4].name, "🎲 Maximums celkem")
        self.assertEqual(embed.fields[4].value, "100")  # Convert expected value to string

if __name__ == '__main__':
    unittest.main()
