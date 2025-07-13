import argparse
import os
import json
import time
import nodriver as uc

async def main():
	url = "https://www.oh.bet365.com/#/AC/B12/C20426855/D47/E120593/F47/N7/"

	driver = await uc.start(no_sandbox=True)
	page = await driver.get(url)

	await page.wait_for(selector=".msl-ShowMoreLink")
	showMore = await page.query_selector_all(".msl-ShowMore_Link")

	await ShowMore[0].scroll_into_view()
	await showMore[0].mouse_click()

	time.sleep(20)

	driver.quit()

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("--year", "-y")

	args = parser.parse_args()

	sundays = [
		"2015-07-12",
		"2016-07-10",
		"2017-07-09",
		"2018-07-15",
		"2019-07-07",
		"2020-07-12",
		"2021-07-11",
		"2022-07-17",
		"2023-07-09",
		"2024-07-14"
	]
	for dt in sundays:
		year,m,d = map(str, dt.split("-"))
		with open(f"static/splits/mlb_feed/{year}.json") as fh:
			feed = json.load(fh)

		if dt not in feed:
			continue

		dayBefore = int(dt.split("-")[-1]) - 1
		print(int(feed[f"{year}-{m}-{dayBefore:02d}"]["hr"]) / feed[f"{year}-{m}-{dayBefore:02d}"]["totGames"])
		twoDayBefore = int(dt.split("-")[-1]) - 2
		print(int(feed[f"{year}-{m}-{twoDayBefore:02d}"]["hr"]) / feed[f"{year}-{m}-{twoDayBefore:02d}"]["totGames"])
		print(dt, feed[dt]["hr"], feed[dt]["totGames"], int(feed[dt]["hr"]) / feed[dt]["totGames"])

		x = []
		for d in feed:
			try:
				x.append((int(feed[d]["hr"]) / feed[d]["totGames"], d, feed[d]["hr"]))
			except:
				pass
		#print(sorted(x))
		
