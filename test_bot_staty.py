import unittest
import discord
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from bot_staty import (
    fetch_player_data,
    fetch_additional_stats,
    fill_missing_stats,
    create_embed,
    create_premium_embed,
    create_comparison_embed,
    fetch_last_matches,
    get_data
)

class TestFetchPlayerData(unittest.IsolatedAsyncioTestCase):

    @patch('bot_staty.get_data', new_callable=AsyncMock)
    async def test_fetch_player_data(self, mock_get_data):
        # Mock the API responses
        mock_get_data.side_effect = [
            [{"player_name": "Test Player", "player_key": "12345"}],
            [["Averages", "50", "60"], ["Checkout Pcnt", "40%", "50%"]],
            {"data": [{"opponent": "<b>Knight</b>", "match_date": "2023-02-01",
                       "loser_score": 2, "winner_score": 3, "stat1": 5}]},
            # ...simulate calls for stats_urls...
            {"data": [{"player_name": "Test Player", "stat": 100}]},
            {"data": [{"player_name": "Test Player", "stat": 110}]},
            {"data": [{"player_name": "Test Player", "stat": 20}]},
            {"data": [{"player_name": "Test Player", "stat": 30}]},
            {"data": [{"player_name": "Test Player", "stat": 0.25}]},
            {"data": [{"player_name": "Test Player", "stat": 0.35}]}
        ]

        player_name = "Test Player"
        date_from = "2025-01-01"
        date_to = "2025-01-10"

        player_data = await fetch_player_data(player_name, date_from, date_to)
        self.assertEqual(player_data["player_key"], "12345")
        self.assertIn("additional_stats", player_data)
        self.assertIn("last_matches", player_data)

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

    def test_fill_missing_stats_new(self):
        data = {
            "additional_stats": {
                "Averages": ["50", "60", "70"],
                "Checkout Pcnt": ["40%", "50%", "60%"],
                "180's per leg": ["0.2", "0.3", "0.4"]
            }
        }
        fill_missing_stats(data)
        self.assertEqual(data["average"], 60.0)
        self.assertEqual(data["checkout_pcnt"], "50.00%")

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

    def test_create_embed_basic(self):
        data = {"player_name": "Tester", "rank": 5, "average": 55.0}
        embed = create_embed("Tester", data, discord.Color.blue(), "Test Desc")
        self.assertIn("Statistics for player Tester", embed.title)
        self.assertEqual(embed.fields[0].name, "🏆 Rank")
        self.assertEqual(embed.fields[0].value, "5")

class TestCreatePremiumEmbed(unittest.TestCase):
    def test_create_premium_embed_basic(self):
        data = {"player_name": "Tester", "rank": 2, "average": 80.0}
        embed = create_premium_embed("Tester", data)
        self.assertIn("Premium statistics for player Tester", embed.title)
        self.assertEqual(embed.fields[0].name, "🏆 Rank")
        self.assertEqual(embed.fields[0].value, "2")

class TestCreateComparisonEmbed(unittest.TestCase):
    def test_create_comparison_embed(self):
        player1_data = {"rank": 1, "average": 60, "maximums": 40}
        player2_data = {"rank": 2, "average": 55, "maximums": 35}
        embed = create_comparison_embed("P1", player1_data, "P2", player2_data)
        self.assertIn("Player Comparison", embed.title)
        self.assertIn("P1 🆚 P2", embed.fields[0].name)

class TestGetData(unittest.IsolatedAsyncioTestCase):
    @patch("bot_staty.aiohttp.ClientSession.get")
    async def test_get_data_cached(self, mock_get):
        mock_get.return_value.__aenter__.return_value.status = 200
        mock_get.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={"test": "data"}
        )
        url = "http://example.com/cache_test"
        first_result = await get_data(url)
        second_result = await get_data(url)
        self.assertEqual(first_result, {"test": "data"})
        self.assertEqual(second_result, {"test": "data"})
        mock_get.assert_called_once()

class TestFetchLastMatches(unittest.IsolatedAsyncioTestCase):
    @patch("bot_staty.get_data", new_callable=AsyncMock)
    async def test_fetch_last_matches(self, mock_get_data):
        mock_get_data.return_value = {
            "data": [
                {"opponent": "<b>OpponentA</b>", "match_date": "2023-01-01",
                 "loser_score": 2, "winner_score": 3, "stat1": 4},
                {"opponent": "<b>OpponentB</b>", "match_date": "2023-01-02",
                 "loser_score": 1, "winner_score": 3, "stat1": 2},
            ]
        }
        last_matches = await fetch_last_matches(player_key="12345", limit=2)
        self.assertEqual(len(last_matches), 2)
        self.assertEqual(last_matches[0]["opponent"], "OpponentA")
        self.assertEqual(last_matches[0]["legs"], 5)
        self.assertEqual(last_matches[1]["180s"], 2)

if __name__ == '__main__':
    unittest.main()
