import unittest

from agente import Agent, load_games


class CareerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = Agent(load_games())

    def test_career_totals_and_averages(self):
        totals = self.agent.answer("Total de puntos por fase")
        self.assertEqual(totals["filas"], [["Regular", 32292, 1072], ["Playoffs", 5987, 179]])
        average = self.agent.answer("Compara el promedio de puntos en regular y playoffs")
        self.assertEqual(average["filas"], [["Regular", 30.12, 1072], ["Playoffs", 33.45, 179]])
        self.assertEqual(len(self.agent.options["temporada"]), 15)

    def test_shots_and_follow_up(self):
        result = self.agent.answer("¿Cuántos triples anotó en 1996-97?")
        self.assertEqual(result["filas"], [["Regular", 111, 82], ["Playoffs", 13, 19]])
        follow_up = self.agent.answer("¿Y en playoffs?", result["plan"])
        self.assertEqual(follow_up["filas"], [["Playoffs", 13, 19]])
        result = self.agent.answer("Tiros de dos puntos en fase regular")
        self.assertEqual(result["filas"], [["Regular", 11611, 1072]])

    def test_double_double_and_triple_double_are_exclusive(self):
        doubles = self.agent.answer("Dobles-dobles por fase")
        triples = self.agent.answer("Triples-dobles por fase")
        self.assertEqual(doubles["filas"], [["Regular", 172, 1072], ["Playoffs", 37, 179]])
        self.assertEqual(triples["filas"], [["Regular", 28, 1072], ["Playoffs", 2, 179]])
        self.assertFalse(any(r["dd"] and r["td"] for r in self.agent.games))
        with self.assertRaisesRegex(ValueError, "tiros de dos"):
            self.agent.answer("¿Cuántos dobles hizo?")

    def test_records_and_threshold_boundary(self):
        top = self.agent.answer("Top 5 partidos por puntos contra los Celtics")
        self.assertEqual(top["filas"][0], ["1986-04-20", "1985-86", "Playoffs", "Bulls", "Boston Celtics", 63])
        self.assertEqual(len(top["filas"]), 5)
        by_city = self.agent.answer("Enséñame sus actuaciones de mayor anotación frente a Boston.")
        self.assertEqual(by_city["filas"][0], top["filas"][0])
        record = self.agent.answer("Récord de puntos en temporada regular")
        self.assertIn("1990-03-28 vs. Cleveland Cavaliers", record["mensaje"])
        max_playoffs = self.agent.answer("Máximo de puntos por partido en playoffs")
        self.assertEqual(max_playoffs["filas"], [["Playoffs", 63, 179]])
        inclusive = self.agent.answer("¿Cuántos partidos con al menos 40 puntos en playoffs?")
        exclusive = self.agent.answer("¿Cuántos partidos con más de 40 puntos en playoffs?")
        self.assertEqual(inclusive["filas"], [["Playoffs", 38, 179]])
        self.assertEqual(exclusive["filas"], [["Playoffs", 35, 179]])

    def test_empty_result_and_invalid_plan(self):
        empty = self.agent.answer("Puntos en 1994-95 con Wizards")
        self.assertEqual(empty["base"], 0)
        self.assertEqual(empty["grafica"], [])
        with self.assertRaisesRegex(ValueError, "fuera del catálogo"):
            self.agent.answer("¿Y en playoffs?", dict(empty["plan"], metrica="invalid"))


if __name__ == "__main__":
    unittest.main()
