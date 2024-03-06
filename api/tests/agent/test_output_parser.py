import unittest

from pybot.agent.output_parser import DictOutputParser, find_dicts


class TestJsonOutputParser(unittest.TestCase):
    def test_parse_until_valid(self):
        parser = DictOutputParser()
        output = """Alright, let\'s use the python tool to analyze the dataset and find the team with the highest number of victories.\n\nFirst, we need to read the dataset into a pandas DataFrame. Here\'s the code to do that:\n\n```python\nimport pandas as pd\n\n# read the file\ndf = pd.read_csv(\'/mnt/shared/results.csv\')\n```\n\nNext, we need to group the DataFrame by the \'home_team\' and \'away_team\' columns, and then count the number of victories for each team. Here\'s the code to do that:\n\n```python\n# group by home_team and away_team, and count the number of victories for each team\nteam_victories = df.groupby([\'home_team\', \'away_team\']).size().unstack(fill_value=0)\nteam_victories.loc[team_victories.index.levels[0], \'victories\'] = team_victories.sum(axis=1)\n```\n\nFinally, we can find the team with the highest number of victories by using the `idxmax` function:\n\n```python\n# find the team with the highest number of victories\nwinner = team_victories[\'victories\'].idxmax()\n\n# print the winner\nprint(f"The team with the highest number of victories is {winner}.")\n```\n\nSo, the complete code to find the team with the highest number of victories is:\n\n```python\nimport pandas as pd\n\n# read the file\ndf = pd.read_csv(\'/mnt/shared/results.csv\')\n\n# group by home_team and away_team, and count the number of victories for each team\nteam_victories = df.groupby([\'home_team\', \'away_team\']).size().unstack(fill_value=0)\nteam_victories.loc[team_victories.index.levels[0], \'victories\'] = team_victories.sum(axis=1)\n\n# find the team with the highest number of victories\nwinner = team_victories[\'victories\'].idxmax()\n\n# print the winner\nprint(f"The team with the highest number of victories is {winner}.")\n```\n\nNow, let\'s execute this code using the python tool:\n\n```json\n{\n    "tool_name": "python",\n    "tool_input": "import pandas as pd\\n\\n# read the file\\ndf = pd.read_csv(\'/mnt/shared/results.csv\')\\n\\n# group by home_team and away_team, and count the number of victories for each team\\nteam_victories = df.groupby([\'home_team\', \'away_team\']).size().unstack(fill_value=0)\\nteam_victories.loc[team_victories.index.levels[0], \'victories\'] = team_victories.sum(axis=1)\\n\\n# find the team with the highest number of victories\\nwinner = team_victories[\'victories\'].idxmax()\\n\\n# print the winner\\nprint(f\\"The team with the highest number of victories is {winner}.\\")"\n}\n```\n\nThis should give you the team with the highest number of victories in the dataset."""
        parsed = parser.parse(output)
        self.assertEqual(parsed.tool, "python")

    def test_parse_until_valid2(self):
        parser = DictOutputParser()
        output = """I apologize if my earlier suggestion was confusing, here\'s an updated version using python:\n\nFor python tool to count the number of lines in the given file on your specified path, I need to provide the following:\n\n```python\nimport io\nimport pandas as pd\n\nfile_path = \'/mnt/shared/test.txt\'\n\nwith io.open(file_path, encoding=\'utf-8\') as fin:\n    print(f\'Number of rows in {file_path}: {len(fin.readlines())}\')\n```\n\n{\n    "tool_name": "python",\n    "tool_input": "import io\\nimport pandas as pd\\n\\nfile_path = \'/mnt/shared/test.txt\'\\n\\nwith io.open(file_path, encoding=\'utf-8\') as fin:\\n    print(f\'Number of rows in {file_path}: {len(fin.readlines())}\')"\n}"""
        parsed = parser.parse(output)
        self.assertEqual(parsed.tool, "python")

    def test_parse(self):
        parser = DictOutputParser()
        output = """ To create a dataframe in Python, you can use the pandas library. Here\'s an example of creating a dataframe with two columns, one for \'Name\' and another for \'Age\':\n\n```python\nimport pandas as pd\n\ndata = [\n    {\'Name\': \'Alice\', \'Age\': 25},\n    {\'Name\': \'Bob\', \'Age\': 30},\n    {\'Name\': \'Charlie\', \'Age\': 28}\n]\n\ndf = pd.DataFrame(data)\n```\n\nNow, the dataframe \'df\' contains the data in a structured format, which can be easily manipulated and analyzed.\n\nTo use this example in python, you can send the following message:\n\n```\n{\n  "tool_name": "python",\n  "tool_input": "import pandas as pd\\n\\ndata = [{\\n    \'Name\': \'Alice\', \'Age\': 25},\\n    {\\n    \'Name\': \'Bob\', \'Age\': 30},\\n    {\\n    \'Name\': \'Charlie\', \'Age\': 28}\\n]\\n\\ndf = pd.DataFrame(data)"\n}\n```\n\npython will execute the Python code and return the output."""
        parsed = parser.parse(output)
        self.assertEqual(parsed.tool, "python")


if __name__ == "__main__":
    unittest.main()
