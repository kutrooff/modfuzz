import matplotlib.pyplot as plt
import pandas as pd
import matplotlib

class ReportBuilder:
    def __init__(self, history):
        self.history = history

    def save_history_csv(self, path="fuzz_history.csv"):
        df = pd.DataFrame([{
            "url": rec["request"].url,
            "method": rec["request"].method,
            "status": rec["response"].status_code
        } for rec in self.history])
        df.to_csv(path, index=False)

    def generate_stats(self):
        df = pd.DataFrame([rec["response"].status_code for rec in self.history], columns=["status"])
        return df["status"].value_counts()

    def plot_status_distribution(self):
        stats = self.generate_stats()
        stats.plot(kind="bar")
        plt.savefig("status_distribution.png")
