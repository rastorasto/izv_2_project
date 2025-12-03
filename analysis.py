#!/usr/bin/env python3
# coding=utf-8

from matplotlib import pyplot as plt
import pandas as pd
import seaborn as sns
import numpy as np
import zipfile

# muzete pridat libovolnou zakladni knihovnu ci knihovnu predstavenou na prednaskach
# dalsi knihovny pak na dotaz

# Ukol 1: nacteni dat ze ZIP souboru


def load_data(filename: str, ds: str) -> pd.DataFrame:
    # Extracted folder names
    years = ['2023', '2024', '2025']
    # Dataframe holder
    dfs = []
    
    with zipfile.ZipFile(filename, 'r') as zf:
        # Go through each year
        for year in years:
            # Create file name
            file_name = f'{year}/I{ds}.xls'
            # Read file
            with zf.open(file_name) as f:
                # Read html file with encoding using pandas
                df = pd.read_html(f, encoding='cp1250')[0]
                # Clean column name
                df.columns = df.columns.str.strip()
                # Remove unnamed columns regex matches empty or Unnamed something
                df = df.loc[:, ~df.columns.str.contains('^$|^Unnamed')]
                # Append to list
                dfs.append(df)
    
    # Concatenate all dataframes
    return pd.concat(dfs, ignore_index=True)

# Ukol 2: zpracovani dat


def parse_data(df: pd.DataFrame, verbose: bool = False) -> pd.DataFrame:
    df = df.copy()
    df['date'] = pd.to_datetime(df['p2a'], format='%d.%m.%Y')

    region = {0: "PHA", 1: "STC", 2: "JHC", 3: "PLK", 4: "ULK", 5: "HKK",6: "JHM", 7: "MSK", 14: "OLK", 15: "ZLK", 16: "VYS", 17: "PAK", 18: "LBK", 19: "KVK"} 
    df['region'] = df['p4a'].map(region)

    df = df.drop_duplicates(subset=['p1'])

    if verbose:
        size = df.memory_usage(deep=True).sum() / (1024 ** 2) # Bytes to MB 
        print(f"new_size={size:.1f} MB")

    return df

# Ukol 3: počty nehod v jednotlivých regionech podle stavu řidiče
def plot_state(df: pd.DataFrame, df_vehicles : pd.DataFrame, fig_location: str = None,
                    show_figure: bool = False):
    print("plot")
    merge = df.merge(df_vehicles, left_on='p1', right_on='p1', how='inner')
    print(merge)
    merge = merge[merge['p57'].between(3, 9)]

    driver_state = {
        3: "Under the influence of drugs",
        4: "Under the influence of alcohol 0.99‰ or less",
        5: "Under the influence of alcohol 1‰ or more",
        6: "Sickness or injury",
        7: "Ivalidity",
        8: "Died during the accident (stroke ...)",
        9: "Suicide attempt or suicide"
    }

    merge['state'] = merge['p57'].map(driver_state)

    # Since there are 7 graphs in total but the assignment wants only 6 i will choose the graphs with the most values
    top_states = merge['state'].value_counts().head(6).index

    # Merge will now contain just the top states
    merge = merge[merge['state'].isin(top_states)]

    counts = merge.groupby(['region', 'state']).size().reset_index(name='count')

    ordered_regions = sorted(counts['region'].unique())

    g = sns.catplot(data=counts, x='region', y='count', col='state', kind='bar', hue='region', palette='tab10', sharey=False, col_wrap=2, height=3, order=ordered_regions, hue_order=ordered_regions)
    
    g.set_axis_labels('Region', 'Number of accidents')
    g.set_titles('{col_name}')

    plt.tight_layout()

    if fig_location:
        plt.savefig(fig_location)
    if show_figure:
        plt.show()

    plt.close()

# Ukol4: alkohol a roky v krajích
def plot_alcohol(df: pd.DataFrame, df_consequences : pd.DataFrame, 
                 fig_location: str = None, show_figure: bool = False):
    merge = df.merge(df_consequences, left_on='p1', right_on='p1', how='inner')

    injury = {
        1: "Death",
        2: "Heavy injury",
        3: "Light injury",
        4: "No injury"
    }
    
    merge['injury'] = merge['p59g'].map(injury)

    merge['year'] = merge['date'].dt.year
    merge["month"] = merge["date"].dt.month

    merge = merge[(merge['p11'] >=3) & (merge['month'] <= 10)]

    counts = merge.groupby(['region', 'year', 'injury']).size().reset_index(name='count')

    ordered_regions = sorted(counts['region'].unique())

    g = sns.catplot(data=counts, x='region', y='count', hue='year', col='injury', kind='bar', col_wrap=2, height=3, aspect=1.5, palette='Set2', sharey=False, order=ordered_regions)
    g.set_axis_labels('Region', 'Number of accidents')
    g.set_titles('{col_name}')

    plt.tight_layout()
    
    if fig_location:
        plt.savefig(fig_location)
    if show_figure:
        plt.show()
    plt.close()

# Ukol 5: Podmínky v čase
def plot_conditions(df: pd.DataFrame, fig_location: str = None,
                    show_figure: bool = False):
    # Choose these 4 regions because they were choosed in the assignment example
    regions = ['JHM', 'MSK', 'OLK', 'ZLK']
    df_filtered = df[df['region'].isin(regions)].copy()
    
    # 1	neztížené
    # 2	mlha
    # 3	na počátku deště, slabý déšť, mrholení apod.
    # 4	déšť
    # 5	sněžení
    # 6	tvoří se námraza, náledí
    # 7	nárazový vítr (boční, vichřice apod.)
    # 0	jiné ztížené

    # Map conditions
    condition_map = {
        1: 'None',
        2: 'Fog',
        3: 'At the beggining of rain',
        4: 'Rain',
        5: 'Snow',
        6: 'Freezing rain',
        7: 'Strong wind',
        0: 'Other'
    }

    # p18	POVĚTRNOSTNÍ PODMÍNKY V DOBĚ NEHODY	
    # Assignment is wrong i changed p11 to p17
    df_filtered['condition'] = df_filtered['p18'].map(condition_map)
    
    # Pivot table
    pivot = df_filtered.pivot_table(values='p1', index=['date', 'region'], columns='condition', aggfunc='count', fill_value=0).reset_index()
    
    # Resample to month
    pivot['date'] = pd.to_datetime(pivot['date'])
    monthly = pivot.groupby(['region', pd.Grouper(key='date', freq='ME')]).sum().reset_index()
    
    # Melt
    melted = monthly.melt(id_vars=['region', 'date'], var_name='condition', value_name='count')
    
    # Date range
    melted = melted[(melted['date'] >= '2023-01-01') & (melted['date'] < '2025-01-01')]

    ordered_regions = sorted(melted['region'].unique())
    
    g = sns.relplot(
        data=melted,
        x='date', y='count', hue='condition', col='region', kind='line',
        col_wrap=2, height=3, aspect=1.5, palette='Set2',
        facet_kws={'sharey': False, 'legend_out': True}, col_order=ordered_regions
    )

    for ax in g.axes.flat:
        ax.grid(False)
        ax.set_facecolor('#f9f9f9')

    # g._legend.set_bbox_to_anchor((1.05, 0.5))
    # plt.subplots_adjust(right=0.8)

    g.set_axis_labels('Date', 'Number of accidents')
    g.set_titles('{col_name}')


    # Place a single legend to the right, outside the grid
    # Add legend (created on FacetGrid's figure) and anchor it
    # g.add_legend()
    # if g._legend is not None:
    #     g._legend.set_bbox_to_anchor((1.02, 0.5))
    #     g._legend.set_loc('center left')
    # # Create space on the right for the legend box
    # g.fig.subplots_adjust(right=0.82)

    # plt.tight_layout()
    
    if fig_location:
        plt.savefig(fig_location)
    if show_figure:
        plt.show()
    plt.close()



if __name__ == "__main__":
    # zde je ukazka pouziti, tuto cast muzete modifikovat podle libosti
    # skript nebude pri testovani pousten primo, ale budou volany konkreni
    # funkce.

    print("Before loading accidents")
    df = load_data("data_23_25.zip", "nehody")
    print("Data loaded")
    print(df);
    print("Loading consequences")
    df_consequences = load_data("data_23_25.zip", "nasledky")
    print(df_consequences);
    print("Loading vehicles")
    df_vehicles = load_data("data_23_25.zip", "Vozidla")
    print(df_vehicles);
    # print(f"before size {df.memory_usage(deep=True).sum() / (1024**2):.1f} MB")
    print("Before parsing")
    df2 = parse_data(df, True)
    print("Data parsed")
    print(df2);
    
    # plot_state(df2, df_vehicles, "01_state.png")
    plot_state(df2, df_vehicles, None, True)
    plot_alcohol(df2, df_consequences, "02_alcohol.png", True)
    plot_conditions(df2, "03_conditions.png", True)

# Poznamka:
# pro to, abyste se vyhnuli castemu nacitani muzete vyuzit napr
# VS Code a oznaceni jako bunky (radek #%%% )
# Pak muzete data jednou nacist a dale ladit jednotlive funkce
# Pripadne si muzete vysledny dataframe ulozit nekam na disk (pro ladici
# ucely) a nacitat jej naparsovany z disku
