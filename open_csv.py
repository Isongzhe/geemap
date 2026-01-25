
dataset = "/home/NAS/homes/isaac-10009/Data/Sinotech_Hackathon/Glofas_analogue_results_hybas_si_lev08_3080576250_target_rp_100_df.csv"

import pandas as pd

df = pd.read_csv(dataset)
print(df.head(10))