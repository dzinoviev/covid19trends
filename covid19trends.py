import json
import bs4
import requests
import pandas as pd
import scipy
import matplotlib.pyplot as plt

# Get state names
states = pd.read_csv("states.csv")

# Use dirty hacks to extract dates and cases
def get_state_data(state0):
    state = state0.replace(" ", "-")
    print(state0)
    state_data = requests.get(f"https://www.worldometers.info/coronavirus/usa/{state}/")
    text = bs4.BeautifulSoup(state_data.text, "lxml")
    data = text.find("h3", text=f"Daily New Cases in {state0}").next_sibling.next_sibling.next_sibling.next_sibling.string
    
    dates = json.loads(data[data.find("categories:") + 12: data.find("yAxis:") - 14])
    cases = json.loads(data[data.find("data:") + 6: data.find("3-day moving average")-44])
    
    data_d = text.find("h3", text=f"Daily New Deaths in {state0}").next_sibling.next_sibling.next_sibling.next_sibling.string
    deaths = json.loads(data_d[data_d.find("data:") + 6: data_d.find("3-day moving average") - 44])
    df = pd.DataFrame({"cases": cases, "deaths": deaths}, index=dates)
    df.index = pd.DatetimeIndex(df.index+", 2020")
    
    tail = df.resample("1W").mean().iloc[-5: -1]["cases"]
    poly = scipy.polyfit(range(tail.shape[0]), tail.values, 1)
    return poly

# Get trends
trends = states.State.apply(get_state_data)
states = states.join(trends.apply(pd.Series))
states.columns = "State", "Abbreviation", "slope", "start"
states.set_index("State", inplace=True)
states["slope_rel"] = states["slope"] / states["start"]
states = states.sort_values("slope_rel")

# Plotting
import datetime
import cartopy.crs as ccrs
import cartopy.io.shapereader as shpreader

popdensity = ((states["slope_rel"] + 1) / 2).to_dict()
fig = plt.figure()
ax = fig.add_axes([0, 0, 1, 1], projection=ccrs.LambertConformal())

ax.set_extent([-125, -66.5, 20, 50], ccrs.Geodetic())

shapename = "admin_1_states_provinces_lakes_shp"
states_shp = shpreader.natural_earth(resolution="110m",
                                     category="cultural", name=shapename)
ax.background_patch.set_visible(True)
ax.outline_patch.set_visible(True)
today = datetime.date.today().strftime("%Y-%m-%d")
ax.set_title(f"# of COVID-19 cases change rate over the last month ({today})")

for astate in shpreader.Reader(states_shp).records():
    state_dens = popdensity.get(astate.attributes["name"], 0)
    facecolor = plt.cm.seismic(state_dens)
    ax.add_geometries([astate.geometry], ccrs.PlateCarree(),
                      facecolor=facecolor, edgecolor="black")

plt.savefig(f"covid-rates-{today}.png", dpi=100)
plt.show()
