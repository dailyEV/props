
from datetime import datetime,timedelta
from subprocess import call
from bs4 import BeautifulSoup as BS
import math
import json
import os
import re
import argparse
import unicodedata
import nodriver as uc
import queue
import threading
import time

try:
	from shared import *
except:
	from controllers.shared import *

q = queue.Queue()
lock = threading.Lock()

def devig(evData, player="", ou="575/-900", finalOdds=630, prop="hr", book=""):

	prefix = ""

	impliedOver = impliedUnder = 0
	over = int(ou.split("/")[0])
	if over > 0:
		impliedOver = 100 / (over+100)
	else:
		impliedOver = -1*over / (-1*over+100)

	bet = 100
	profit = finalOdds / 100 * bet
	if finalOdds < 0:
		profit = 100 * bet / (finalOdds * -1)

	if "/" not in ou:
		u = 1.07 - impliedOver
		if u > 1:
			return
		if over > 0:
			under = int((100*u) / (-1+u))
		else:
			under = int((100 - 100*u) / u)
	else:
		under = int(ou.split("/")[1])


	if under > 0:
		impliedUnder = 100 / (under+100)
	else:
		impliedUnder = -1*under / (-1*under+100)

	x = impliedOver
	y = impliedUnder
	while round(x+y, 8) != 1.0:
		k = math.log(2) / math.log(2 / (x+y))
		x = x**k
		y = y**k

	dec = 1 / x
	if dec >= 2:
		fairVal = round((dec - 1)  * 100)
	else:
		fairVal = round(-100 / (dec - 1))
	#fairVal = round((1 / x - 1)  * 100)
	implied = round(x*100, 2)
	#ev = round(x * (finalOdds - fairVal), 1)

	#multiplicative 
	mult = impliedOver / (impliedOver + impliedUnder)
	add = impliedOver - (impliedOver+impliedUnder-1) / 2

	evs = []
	for method in [x, mult, add]:
		ev = method * profit + (1-method) * -1 * bet
		ev = round(ev, 1)
		evs.append(ev)

	ev = min(evs)

	if book:
		prefix = book+"_"

	if player not in evData:
		evData[player] = {}
	evData[player][f"{prefix}fairVal"] = fairVal
	evData[player][f"{prefix}implied"] = implied
	
	evData[player][f"{prefix}ev"] = ev

def convertDecOdds(odds):
	if odds == 0:
		return 0
	if odds > 0:
		decOdds = 1 + (odds / 100)
	else:
		decOdds = 1 - (100 / odds)
	return decOdds

def convertAmericanOdds(avg):
	if avg >= 2:
		avg = (avg - 1) * 100
	else:
		avg = -100 / (avg - 1)
	return round(avg)

def strip_accents(text):
	try:
		text = unicode(text, 'utf-8')
	except NameError: # unicode is a default on python 3 
		pass

	text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode("utf-8")

	return str(text)

def parsePlayer(player):
	player = strip_accents(player).lower().replace(".", "").replace("'", "").replace("-", " ").replace(" jr", "").replace(" sr", "").replace(" iii", "").replace(" ii", "").replace(" iv", "")
	if player.endswith(" v"):
		player = player[:-2]
	return player

def convertTeam(team):
	team = team.lower().replace(".", "").replace(" ", "")
	t = team.split(" ")[0][:3]
	if t in ["gre", "gbp"]:
		return "gb"
	elif t == "jac":
		return "jax"
	elif t == "nep":
		return "ne"
	elif t == "nos":
		return "no"
	elif t in ["kan", "kcc"]:
		return "kc"
	elif t in ["tam", "tbb"]:
		return "tb"
	elif t in ["san", "sf4"]:
		return "sf"
	elif t in ["las", "lvr"]:
		return "lv"
	elif t == "los":
		if "rams" in team:
			return "lar"
		return "lac"
	elif t == "new":
		if "giants" in team:
			return "nyg"
		elif "jets" in team:
			return "nyj"
		elif "saints" in team:
			return "no"
		return "ne"
	return t

def writeESPN():
	js = """

	{
		function convertTeam(team) {
			team = team.toLowerCase();
			t = team.split(" ")[0];
			if (t == "ny") {
				if (team.includes("giants")) {
					return "nyg";
				}
				return "nyj";
			} else if (t == "la") {
				if (team.includes("rams")) {
					return "lar";
				}
				return "lac";
			}
			return t;
		}

		function parsePlayer(player) {
			player = player.toLowerCase().split(" (")[0].replaceAll(".", "").replaceAll("'", "").replaceAll("-", " ").replaceAll(" jr", "").replaceAll(" sr", "").replaceAll(" iii", "").replaceAll(" ii", "").replaceAll(" iv", "");
			return player;
		}

		let status = "";

		async function readPage() {
			for (detail of document.querySelectorAll("details")) {
				let prop = detail.querySelector("h2").innerText.toLowerCase();

				let skip = 2;
				let player = "";
				if (prop.indexOf("player") == 0) {
					prop = prop.replace("player total ", "").replace("player ", "").replace(" + ", "+").replace("points", "pts").replace("field goals made", "fgm").replace("extra pts made", "xp").replace("passing", "pass").replace("rushing", "rush").replace("receptions", "rec").replace("reception", "rec").replace("receiving", "rec").replace("attempts", "att").replace("interceptions thrown", "int").replace("completions", "cmp").replace("completion", "cmp").replace("yards", "yd").replace("touchdowns", "td").replace("assists", "ast").replaceAll(" ", "_");
				} else {
					continue;
				}

				let open = detail.getAttribute("open");
				if (open == null) {
					detail.querySelector("summary").click();
					while (detail.querySelectorAll("button").length == 0) {
						await new Promise(resolve => setTimeout(resolve, 500));
					}
				}

				if (!data[prop]) {
					data[prop] = {};
				}

				let btns = detail.querySelectorAll("button");
				let seeAll = false;
				if (btns[btns.length - 1].innerText == "See All Lines") {
					seeAll = true;
					btns[btns.length - 1].click();
				}

				if (seeAll) {
					let modal = document.querySelector(".modal--see-all-lines");
					while (!modal) {
						await new Promise(resolve => setTimeout(resolve, 700));
						modal = document.querySelector(".modal--see-all-lines");
					}

					while (modal.querySelectorAll("button").length == 0) {
						await new Promise(resolve => setTimeout(resolve, 700));
					}

					let btns = Array.from(modal.querySelectorAll("button"));
					btns.shift();

					for (i = 0; i < btns.length; i += 3) {
						let ou = btns[i+1].querySelectorAll("span")[1].innerText+"/"+btns[i+2].querySelectorAll("span")[1].innerText;
						let player = parsePlayer(btns[i].innerText.toLowerCase().split(" total ")[0]);
						let line = btns[i+1].querySelector("span").innerText.split(" ")[1];
						data[prop][player] = {};
						data[prop][player][line] = ou.replace("Even", "+100");
					}
					modal.querySelector("button").click();
					while (document.querySelector(".modal--see-all-lines")) {
						await new Promise(resolve => setTimeout(resolve, 500));
					}
				}
			}
			console.log(data);
		}

		readPage();
	}

"""

def runMGM():
	uc.loop().run_until_complete(writeMGM())

async def writeMGM():
	book = "mgm"

	browser = await uc.start(no_sandbox=True)
	while True:
		data = nested_dict()

		url = q.get()
		if url is None:
			q.task_done()
			break

		url = f"https://www.mi.betmgm.com/en/sports/events/{url}?market=-1"
		page = await browser.get(url)
		try:
			await page.wait_for(selector=".event-details-pills-list")
		except:
			q.task_done()
			continue

		groups = await page.query_selector_all(".option-group-column")
		for groupIdx, group in enumerate(groups):
			if not group:
				continue
			panels = [x for x in group.children if x.tag != "#comment"]
			for panelIdx, panel in enumerate(panels):
				prop = [x for x in panel.children if x.tag != "#comment"][0]
				if not prop:
					continue
				prop = prop.text_all.lower()

				up = await panel.query_selector("svg[title=theme-up]")
				if not up:
					up = await panel.query_selector(".clickable")
					try:
						await up.click()
						await page.wait_for(selector=f".option-group-column:nth-child({groupIdx+1}) ms-option-panel:nth-child({panelIdx+1}) .option")
					except:
						continue

				show = await panel.query_selector(".show-more-less-button")
				if show and show.text_all == "Show More":
					await show.click()
					await show.scroll_into_view()
					time.sleep(0.75)

				lis = await panel.query_selector_all("li")
				for li in lis:
					await li.click()
					time.sleep(0.5)
					prop = convertProp(li.text.strip())
					odds = await panel.query_selector_all("ms-option")
					players = await panel.query_selector_all(".player-props-player-name")
					for i in range(0, len(odds), 2):
						line = await odds[i].query_selector(".name")
						fullLine = line.text
						line = str(float(fullLine.strip().split(" ")[-1]))
						over = odds[i].text_all.replace(fullLine, "").strip()
						under = odds[i+1].text_all.replace(fullLine.replace("O", "U"), "").strip()
						player = parsePlayer(players[i//2].text.strip())
						data[prop][player][line] = over+"/"+under

		updateData(book, data)
		q.task_done()

	browser.stop()

def writeDK(debug=False):

	mainCats = {
		"winner": 484,
		"top finish": 1578,
		"make/miss": 699,
		"round props": 1129
	}
	
	subCats = {
		484: [4508],
		1578: [15786],
		699: [18081, 6023],
		1129: [11015, 17299]
	}

	propIds = {
		4508: "win",
		15786: "top_finish",
		18081: "make_cut",
		6023: "miss_cut",
		11015: "rd1",
		17299: "rd1_birdies+"
	}

	if debug:
		mainCats = {
			"round props": 1129
		}

		subCats = {
			699: [18081, 6023],
			1129: [17299]
		}

	res = nested_dict()
	for mainCat in mainCats:
		for subCat in subCats.get(mainCats[mainCat], [0]):
			url = f"https://sportsbook-nash.draftkings.com/api/sportscontent/dkusmi/v1/leagues/24222/categories/{mainCats[mainCat]}"
			if subCat:
				url += f"/subcategories/{subCat}"
			url += "?format=json"
			outfile = "outfuture"
			cookie = "-H 'Cookie: hgg=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ2aWQiOiIxODU4ODA5NTUwIiwiZGtzLTYwIjoiMjg1IiwiZGtlLTEyNiI6IjM3NCIsImRrcy0xNzkiOiI1NjkiLCJka2UtMjA0IjoiNzA5IiwiZGtlLTI4OCI6IjExMjgiLCJka2UtMzE4IjoiMTI2MSIsImRrZS0zNDUiOiIxMzUzIiwiZGtlLTM0NiI6IjEzNTYiLCJka2UtNDI5IjoiMTcwNSIsImRrZS03MDAiOiIyOTkyIiwiZGtlLTczOSI6IjMxNDAiLCJka2UtNzU3IjoiMzIxMiIsImRraC03NjgiOiJxU2NDRWNxaSIsImRrZS03NjgiOiIwIiwiZGtlLTgwNiI6IjM0MjYiLCJka2UtODA3IjoiMzQzNyIsImRrZS04MjQiOiIzNTExIiwiZGtlLTgyNSI6IjM1MTQiLCJka3MtODM0IjoiMzU1NyIsImRrZS04MzYiOiIzNTcwIiwiZGtoLTg5NSI6IjhlU3ZaRG8wIiwiZGtlLTg5NSI6IjAiLCJka2UtOTAzIjoiMzg0OCIsImRrZS05MTciOiIzOTEzIiwiZGtlLTk0NyI6IjQwNDIiLCJka2UtOTc2IjoiNDE3MSIsImRrcy0xMTcyIjoiNDk2NCIsImRrcy0xMTc0IjoiNDk3MCIsImRrcy0xMjU1IjoiNTMyNiIsImRrcy0xMjU5IjoiNTMzOSIsImRrZS0xMjc3IjoiNTQxMSIsImRrZS0xMzI4IjoiNTY1MyIsImRraC0xNDYxIjoiTjZYQmZ6S1EiLCJka3MtMTQ2MSI6IjAiLCJka2UtMTU2MSI6IjY3MzMiLCJka2UtMTY1MyI6IjcxMzEiLCJka2UtMTY1NiI6IjcxNTEiLCJka2UtMTY4NiI6IjcyNzEiLCJka2UtMTcwOSI6IjczODMiLCJka3MtMTcxMSI6IjczOTUiLCJka2UtMTc0MCI6Ijc1MjciLCJka2UtMTc1NCI6Ijc2MDUiLCJka3MtMTc1NiI6Ijc2MTkiLCJka3MtMTc1OSI6Ijc2MzYiLCJka2UtMTc2MCI6Ijc2NDkiLCJka2UtMTc2NiI6Ijc2NzUiLCJka2gtMTc3NCI6IjJTY3BrTWF1IiwiZGtlLTE3NzQiOiIwIiwiZGtlLTE3NzAiOiI3NjkyIiwiZGtlLTE3ODAiOiI3NzMxIiwiZGtlLTE2ODkiOiI3Mjg3IiwiZGtlLTE2OTUiOiI3MzI5IiwiZGtlLTE3OTQiOiI3ODAxIiwiZGtlLTE4MDEiOiI3ODM4IiwiZGtoLTE4MDUiOiJPR2tibGtIeCIsImRrZS0xODA1IjoiMCIsImRrcy0xODE0IjoiNzkwMSIsImRraC0xNjQxIjoiUjBrX2xta0ciLCJka2UtMTY0MSI6IjAiLCJka2UtMTgyOCI6Ijc5NTYiLCJka2gtMTgzMiI6ImFfdEFzODZmIiwiZGtlLTE4MzIiOiIwIiwiZGtzLTE4NDciOiI4MDU0IiwiZGtzLTE3ODYiOiI3NzU4IiwiZGtlLTE4NTEiOiI4MDk3IiwiZGtlLTE4NTgiOiI4MTQ3IiwiZGtlLTE4NjEiOiI4MTU3IiwiZGtlLTE4NjAiOiI4MTUyIiwiZGtlLTE4NjgiOiI4MTg4IiwiZGtoLTE4NzUiOiJZRFJaX3NoSiIsImRrcy0xODc1IjoiMCIsImRrcy0xODc2IjoiODIxMSIsImRraC0xODc5IjoidmI5WWl6bE4iLCJka2UtMTg3OSI6IjAiLCJka2UtMTg0MSI6IjgwMjQiLCJka3MtMTg4MiI6IjgyMzkiLCJka2UtMTg4MSI6IjgyMzYiLCJka2UtMTg4MyI6IjgyNDMiLCJka2UtMTg4MCI6IjgyMzIiLCJka2UtMTg4NyI6IjgyNjQiLCJka2UtMTg5MCI6IjgyNzYiLCJka2UtMTkwMSI6IjgzMjYiLCJka2UtMTg5NSI6IjgzMDAiLCJka2gtMTg2NCI6IlNWbjFNRjc5IiwiZGtlLTE4NjQiOiIwIiwibmJmIjoxNzIyNDQyMjc0LCJleHAiOjE3MjI0NDI1NzQsImlhdCI6MTcyMjQ0MjI3NCwiaXNzIjoiZGsifQ.jA0OxjKzxkyuAktWmqFbJHkI6SWik-T-DyZuLjL9ZKM; STE=\"2024-07-31T16:43:12.166175Z\"; STIDN=eyJDIjoxMjIzNTQ4NTIzLCJTIjo3MTU0NjgxMTM5NCwiU1MiOjc1Mjc3OTAxMDAyLCJWIjoxODU4ODA5NTUwLCJMIjoxLCJFIjoiMjAyNC0wNy0zMVQxNjo0MToxNC42ODc5Mzk4WiIsIlNFIjoiVVMtREsiLCJVQSI6IngxcVNUYXJVNVFRRlo3TDNxcUlCbWpxWFozazhKVmt2OGFvaCttT1ZpWFE9IiwiREsiOiIzMTQyYjRkMy0yNjU2LTRhNDMtYTBjNi00MTEyM2Y5OTEyNmUiLCJESSI6IjEzNTBmMGM0LWQ3MDItNDUwZC1hOWVmLTJlZjRjZjcxOTY3NyIsIkREIjo0NDg3NTQ0MDk4OH0=; STH=3a3368e54afc8e4c0a5c91094077f5cd1ce31d692aaaf5432b67972b5c3eb6fc; _abck=56D0C7A07377CFD1419CD432549CD1DB~0~YAAQJdbOF6Bzr+SQAQAAsmCPCQykOCRLV67pZ3Dd/613rD8UDsL5x/r+Q6G6jXCECjlRwzW7ESOMYaoy0fhStB3jiEPLialxs/UD9kkWAWPhuOq/RRxzYkX+QY0wZ/Uf8WSSap57OIQdRC3k3jlI6z2G8PKs4IyyQ/bRZfS2Wo6yO0x/icRKUAUeESKrgv6XrNaZCr14SjDVxBBt3Qk4aqJPKbWIbaj+1PewAcP+y/bFEVCmbcrAruJ4TiyqMTEHbRtM9y2O0WsTg79IZu52bpOI2jFjEUXZNRlz2WVhxbApaKY09QQbbZ3euFMffJ25/bXgiFpt7YFwfYh1v+4jrIvbwBwoCDiHn+xy17v6CXq5hIEyO4Bra6QT1sDzil+lQZPgqrPBE0xwoHxSWnhVr60EK1X5IVfypMHUcTvLKFcEP2eqwSZ67Luc/ompWuxooaOVNYrgvH/Vvs5UbyVOEsDcAXoyGt0BW3ZVMVPHXS/30dP3Rw==~-1~-1~1722445877; PRV=3P=0&V=1858809550&E=1720639388; ss-pid=4CNl0TGg6ki1ygGONs5g; ab.storage.deviceId.b543cb99-2762-451f-9b3e-91b2b1538a42=%7B%22g%22%3A%22fe7382ec-2564-85bf-d7c4-3eea92cb7c3e%22%2C%22c%22%3A1709950180242%2C%22l%22%3A1709950180242%7D; ab.storage.userId.b543cb99-2762-451f-9b3e-91b2b1538a42=%7B%22g%22%3A%2228afffab-27db-4805-85ca-bc8af84ecb98%22%2C%22c%22%3A1712278087074%2C%22l%22%3A1712278087074%7D; ab.storage.sessionId.b543cb99-2762-451f-9b3e-91b2b1538a42=%7B%22g%22%3A%223eff9525-6179-dc9c-ce88-9e51fca24c58%22%2C%22e%22%3A1722444192818%2C%22c%22%3A1722442278923%2C%22l%22%3A1722442392818%7D; _gcl_au=1.1.386764008.1720096930; _ga_QG8WHJSQMJ=GS1.1.1722442278.7.1.1722442393.19.0.0; _ga=GA1.2.2079166597.1720096930; _dpm_id.16f4=b3163c2a-8640-4fb7-8d66-2162123e163e.1720096930.7.1722442393.1722178863.1f3bf842-66c7-446c-95e3-d3d5049471a9; _tgpc=78b6db99-db5f-5ce5-848f-0d7e4938d8f2; _tglksd=eyJzIjoiYjRkNjE4MWYtMTJjZS01ZDJkLTgwNTYtZWQ2NzIxM2MzMzM2Iiwic3QiOjE3MjI0NDIyNzgyNzEsInNvZCI6IihkaXJlY3QpIiwic29kdCI6MTcyMTg3ODUxOTY5OCwic29kcyI6Im8iLCJzb2RzdCI6MTcyMTg3ODUxOTY5OH0=; _sp_srt_id.16f4=55c32e85-f32f-42ac-a0e8-b1e37c9d3bc6.1720096930.6.1722442279.1722178650.6d45df5a-aea8-4a66-a4ba-0ef841197d1d.cdc2d898-fa3f-4430-a4e4-b34e1909bb05...0; _scid=e6437688-491e-4800-b4b2-e46e81b2816c; _ga_M8T3LWXCC5=GS1.2.1722442279.7.1.1722442288.51.0.0; _svsid=9d0929120b67695ad6ee074ccfd583b7; _sctr=1%7C1722398400000; _hjSessionUser_2150570=eyJpZCI6ImNmMDA3YTA2LTFiNmMtNTFkYS05Y2M4LWNmNTAyY2RjMWM0ZCIsImNyZWF0ZWQiOjE3MjA1NTMwMDE4OTMsImV4aXN0aW5nIjp0cnVlfQ==; _csrf=ba945d1a-57c4-4b50-a4b2-1edea5014b72; ss-id=x8zwcqe0hExjZeHXAKPK; ak_bmsc=F8F9B7ED0366DC4EB63B2DD6D078134C~000000000000000000000000000000~YAAQJdbOF3hzr+SQAQAAp1uPCRjLBiubHwSBX74Dd/8hmIdve4Tnb++KpwPtaGp+NN2ZcEf+LtxC0PWwzhZQ1one2MxGFFw1J6BXg+qiFAoQ6+I3JExoHz4r+gqodWq7y5Iri7+3aBFQRDtn17JMd1PTEEuN8EckzKIidL3ggrEPS+h1qtof3aHJUdx/jkCUjkaN/phWSvohlUGscny8dJvRz76e3F20koI5UsjJ/rQV7dUn6HNw1b5H1tDeL7UR1mbBrCLz6YPDx4XCjybvteRQpyLGI0o9L6xhXqv12exVAbZ15vpuNJalhR6eB4/PVwCmfVniFcr/xc8hivkuBBMOj1lN7ADykNA60jFaIRAY2BD2yj27Aedr7ETAFnvac0L0ITfH20LkA2cFhGUxmzOJN0JQ6iTU7VGgk19FzV+oeUxNmMPX; bm_sz=D7ABF43D4A5671594F842F6C403AB281~YAAQJdbOF3lzr+SQAQAAp1uPCRgFgps3gN3zvxvZ+vbm5t9IRWYlb7as+myjQOyHzYhriG6n+oxyoRdQbE6wLz996sfM/6r99tfwOLP2K8ULgA2nXfOPvqk6BwofdTsUd7KP7EnKhcCjhADO18uKB/QvIJgyS3IFBROxP2XFzS15m/DrRbF7lQDRscWtVo8oOITxNTBlwg0g4fI3gzjG6A4uHYxjeCegxSrHFHGFr4KZXgOnsJhmZe0lqIRWUFcIKC/gfsDd+jfyUnprMso1Flsv9blGlvycOoWTHPdEQvUudpOZlZ3JYz9H5y+dU94wBD9ejxIlRKP26giQISjun829Kt7CuKxJXYAcSJeiomZFh5Abj+Mkv0wi6ZcRcmOVFt49eywPazFHpGM8DVcUkVEFMcpNCeiJ/CtC60U9SoJy+ermF1hTqiAq~3622209~4408134; bm_sv=6618DE86472CB31D7B7F16DAE6689651~YAAQJdbOF96Lr+SQAQAA4iSRCRjfwGUmEhVBbE3y/2VDAAvuPyI2gX7io7CQCPfcdMOnBnNhxHIKYt9PFr7Y1TADQHFUC9kqXu7Nbj9d1BrLlfi1rPbv/YKPqhqSTLkbNSWbeKhKM4HfOu7C+RLV383VzGeyDhc2zOuBKBVNivHMTF9njS3vK6RKeSPFCfxOJdDHgNlIYykf0Ke2WJvflHflTUykwWUaYIlqoB52Ixb9opHQVTptWjetGdYjuOO2S2ZPkw==~1; _dpm_ses.16f4=*; _tgidts=eyJzaCI6ImQ0MWQ4Y2Q5OGYwMGIyMDRlOTgwMDk5OGVjZjg0MjdlIiwiY2kiOiIxZDMxOGRlZC0yOWYwLTUzYjItYjFkNy0yMDlmODEwNDdlZGYiLCJzaSI6ImI0ZDYxODFmLTEyY2UtNWQyZC04MDU2LWVkNjcyMTNjMzMzNiJ9; _tguatd=eyJzYyI6IihkaXJlY3QpIn0=; _tgsid=eyJscGQiOiJ7XCJscHVcIjpcImh0dHBzOi8vc3BvcnRzYm9vay5kcmFmdGtpbmdzLmNvbSUyRmxlYWd1ZXMlMkZiYXNlYmFsbCUyRm1sYlwiLFwibHB0XCI6XCJNTEIlMjBCZXR0aW5nJTIwT2RkcyUyMCUyNiUyMExpbmVzJTIwJTdDJTIwRHJhZnRLaW5ncyUyMFNwb3J0c2Jvb2tcIixcImxwclwiOlwiXCJ9IiwicHMiOiJkOTY4OTkxNy03ZTAxLTQ2NTktYmUyOS1mZThlNmI4ODY3MzgiLCJwdmMiOiIxIiwic2MiOiJiNGQ2MTgxZi0xMmNlLTVkMmQtODA1Ni1lZDY3MjEzYzMzMzY6LTEiLCJlYyI6IjUiLCJwdiI6IjEiLCJ0aW0iOiJiNGQ2MTgxZi0xMmNlLTVkMmQtODA1Ni1lZDY3MjEzYzMzMzY6MTcyMjQ0MjI4MjA3NDotMSJ9; _sp_srt_ses.16f4=*; _gid=GA1.2.150403708.1722442279; _scid_r=e6437688-491e-4800-b4b2-e46e81b2816c; _uetsid=85e6d8504f5711efbe6337917e0e834a; _uetvid=d50156603a0211efbb275bc348d5d48b; _hjSession_2150570=eyJpZCI6ImQxMTAyZTZjLTkyYzItNGMwNy1hNzMzLTcxNDhiODBhOTI4MyIsImMiOjE3MjI0NDIyODE2NDUsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjowLCJzcCI6MH0=; _rdt_uuid=1720096930967.9d40f035-a394-4136-b9ce-2cf3bb298115'"

			time.sleep(0.3)
			os.system(f"curl -s {url} --compressed -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br' -H 'Connection: keep-alive' {cookie} -o {outfile}")

			with open(outfile) as fh:
				data = json.load(fh)

			if debug:
				with open("out", "w") as fh:
					json.dump(data, fh, indent=4)

			if "events" not in data:
				print("events not found")
				continue

			events = {}
			for row in data["events"]:
				events[row["id"]] = row

			markets = {}
			for row in data["markets"]:
				markets[row["id"]] = row

			selections = {}
			for row in data["selections"]:
				selections.setdefault(row["marketId"], [])
				selections[row["marketId"]].append(row)

			for marketId, selections in selections.items():
				market = markets[marketId]
				catId = market["subcategoryId"]
				prop = propIds.get(catId, "")
				event = events[market["eventId"]]
				ps = [x for x in event["participants"] if "metadata" not in x][0]
				player = parsePlayer(ps["name"])
				skip = 2 if prop.startswith("rd1") else 1

				if prop == "win" and market["name"] != "Winner":
					continue

				for idx in range(0, len(selections), skip):
					selection = selections[idx]
					over = selection["displayOdds"]["american"].replace("\u2212", "-")
					ou = over
					player = parsePlayer(selection["participants"][0]["name"])

					if skip == 2:
						line = str(float(selection["points"]))
						res[prop][player][line] = over+"/"+selections[idx+1]["displayOdds"]["american"].replace("\u2212", "-")
					else:
						p = prop
						if p == "top_finish":
							p = convertProp(market["name"])
						res[p][player] = over

	if "miss_cut" in res:
		for p,o in res["make_cut"].items():
			if p in res["miss_cut"]:
				res["make_cut"][p] += "/"+res["miss_cut"][p]
		del res["miss_cut"]
	with open("static/golf/dk.json", "w") as fh:
		json.dump(res, fh, indent=4)

def writePN(debug):
	outfile = "outfuture"

	url = 'curl "https://guest.api.arcadia.pinnacle.com/0.1/leagues/889/matchups?brandId=0" --compressed -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0" -H "Accept: application/json" -H "Accept-Language: en-US,en;q=0.5" -H "Referer: https://www.pinnacle.com/" -H "Content-Type: application/json" -H "X-API-Key: CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R" -H "X-Device-UUID: 66ac2815-a68dc902-a5052c0c-c60f3d05" -H "Origin: https://www.pinnacle.com" -H "Connection: keep-alive" -H "Sec-Fetch-Dest: empty" -H "Sec-Fetch-Mode: cors" -H "Sec-Fetch-Site: same-site" -H "Pragma: no-cache" -H "Cache-Control: no-cache" -o '+outfile

	os.system(url)
	with open(outfile) as fh:
		data = json.load(fh)

	outfile2 = "outfuture2"
	url = 'curl "https://guest.api.arcadia.pinnacle.com/0.1/leagues/889/markets/straight" --compressed -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0" -H "Accept: application/json" -H "Accept-Language: en-US,en;q=0.5" -H "Referer: https://www.pinnacle.com/" -H "Content-Type: application/json" -H "X-API-Key: CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R" -H "X-Device-UUID: 66ac2815-a68dc902-a5052c0c-c60f3d05" -H "Origin: https://www.pinnacle.com" -H "Connection: keep-alive" -H "Sec-Fetch-Dest: empty" -H "Sec-Fetch-Mode: cors" -H "Sec-Fetch-Site: same-site" -H "Pragma: no-cache" -H "Cache-Control: no-cache" -o '+outfile2

	time.sleep(0.2)
	os.system(url)
	with open(outfile2) as fh:
		markets = json.load(fh)

	if debug:
		with open("t", "w") as fh:
			json.dump(data, fh, indent=4)

		with open("t2", "w") as fh:
			json.dump(markets, fh, indent=4)

	res = {}
	propData = {}
	for row in data:
		if "special" not in row:
			continue
		prop = row["special"]["category"].lower()
		desc = row["special"]["description"].lower()
		extra = row["participants"]

		if prop == "regular season wins":
			prop = "wins"
		elif prop == "futures":
			if desc.split(" ")[-2] in ["west", "east", "south", "north"]:
				prop = "division"
			elif desc.split(" ")[-1] == "winner":
				prop = "conference"
			elif "super bowl champion" in desc:
				prop = "superbowl"
		elif "most valuable player" in prop:
			prop = "mvp"
		elif "coach of the year" in prop:
			prop = "coach"
		elif "rookie of the year" in prop:
			if "offensive" in prop:
				prop = "oroy"
			else:
				prop = "droy"
		elif "player of the year" in prop:
			if "offensive" in prop:
				prop = "opoy"
			elif "comeback" in prop:
				prop = "comeback"
			else:
				prop = "dpoy"
		else:
			continue

		propData[row["id"]] = [prop, desc, extra]

	for row in markets:
		if row["matchupId"] not in propData:
			continue
		marketData = propData[row["matchupId"]]
		prop = marketData[0]
		desc = marketData[1]
		extra = marketData[2]
		outcomes = row["prices"]

		if prop not in res:
			res[prop] = {}

		skip = 2
		if prop in ["division", "conference", "superbowl", "mvp", "oroy", "droy", "opoy", "dpoy", "comeback", "coach"]:
			skip = 1

		for i in range(0, len(outcomes), skip):

			ou = str(outcomes[i]["price"])
			line = outcomes[i].get("points", 0)
			if skip == 2:
				ou += f"/{outcomes[i+1]['price']}"
				if (outcomes[i]['participantId'] == extra[0]['id'] and extra[0]['name'] == 'Under') or (outcomes[i]['participantId'] != extra[0]['id'] and extra[0]['name'] == 'Over'):
					ou = f"{outcomes[i+1]['price']}/{outcomes[i]['price']}"

				if line:
					res[prop][convertTeam(desc)] = {
						str(line): ou
					}
			else:
				teamData = [x for x in extra if x["id"] == outcomes[i]["participantId"]][0]
				if prop in ["division", "conference", "superbowl"]:
					res[prop][convertTeam(teamData["name"])] = ou
				else:
					res[prop][parsePlayer(teamData["name"].split(" (")[0])] = ou

	with open("static/golf/pn.json", "w") as fh:
		json.dump(res, fh, indent=4)

def writeKambi():
	outfile = "outfuture"
	url = "https://eu-offering-api.kambicdn.com/offering/v2018/pivuslarl-lbr/listView/american_football/nfl/all/all/competitions.json?lang=en_US&market=US&client_id=2&channel_id=7&ncid=1722267596039"

	os.system(f"curl \"{url}\" -o {outfile}")
	with open(outfile) as fh:
		j = json.load(fh)

	res = {}
	playerMarkets = False
	for event in j["events"]:
		prop = event["event"]["name"].lower()
		eventId = event["event"]["id"]

		player = team = mainProp = ""
		if prop == "super bowl 2024/2025":
			prop = "superbowl"
		elif prop.startswith("afc championship") or prop.startswith("nfc championship"):
			prop = "conference"
		elif prop.startswith("afc") or prop.startswith("nfc"):
			prop = "division"
		elif "mvp" in prop:
			prop = "mvp"
		elif "rookie of the year" in prop:
			if prop.startswith("defensive"):
				prop = "droy"
			else:
				prop = "oroy"
		elif "player of the year" in prop:
			if prop.startswith("defensive"):
				prop = "dpoy"
			elif prop.startswith("comeback"):
				prop = "comeback"
			else:
				prop = "opoy"
		elif prop.startswith("most "):
			prop = prop.split(" 2024")[0].replace("most ", "").replace("points", "pts").replace("passing", "pass").replace("rushing", "rush").replace("receiving", "rec").replace("yards", "yd").replace("touchdowns", "td").replace("interceptions", "int").replace("receptions", "rec")
			prop = prop.replace(" ", "_")
			if prop == "int":
				prop = "def_int"
			elif prop == "int_thrown":
				prop = "int"
			prop = f"most_{prop}"
		elif " markets " in prop:
			if prop.startswith("general") or prop.startswith("world"):
				continue

			if prop.startswith("derrick henry") or prop.startswith("lamar jackson") or prop.startswith("isiah pacheco"):
				playerMarkets = True

			if playerMarkets:
				player = parsePlayer(prop.split(" markets")[0])
			else:
				team = convertTeam(prop.split(" markets")[0])
			mainProp = prop = "market"
		else:
			continue

		#if prop not in ["market"]:
		#	continue

		if prop in ["market"]:
			url = f"https://eu-offering-api.kambicdn.com/offering/v2018/pivuslarl-lbr/betoffer/event/{eventId}.json?includeParticipants=true"
			time.sleep(0.2)
			os.system(f"curl \"{url}\" -o {outfile}")
			with open(outfile) as fh:
				j = json.load(fh)
		else:
			j = event.copy()

		#with open("out", "w") as fh:
		#	json.dump(j, fh, indent=4)
		skip = 1
		if prop in ["market"]:
			skip = 2

		for offerRow in j["betOffers"]:
			outcomes = offerRow["outcomes"]
			offerLabel = offerRow["criterion"]["label"].lower()
			if "games won" in offerLabel:
				prop = "wins"
			elif offerLabel == "to reach the playoffs":
				prop = "playoffs"
			elif offerLabel.startswith("player's total"):
				prop = offerLabel.split(" total ")[-1].split(" - ")[0].replace("points", "pts").replace("passing", "pass").replace("rushing", "rush").replace("receiving", "rec").replace("yards", "yd").replace("touchdowns", "td").replace("interceptions", "int").replace("receptions", "rec")
				prop = prop.replace(" ", "_")
			elif mainProp == "market" and not playerMarkets:
				continue

			if prop not in res:
				res[prop] = {}

			for i in range(0, len(outcomes), skip):
				outcome = outcomes[i]
				if prop == "playoffs":
					res[prop][team] = outcome["oddsAmerican"]+"/"+outcomes[i+1]["oddsAmerican"]
				elif prop == "wins":
					if "line" not in outcome:
						continue
					line = str(outcome["line"] / 1000)
					if team not in res[prop]:
						res[prop][team] = {}
					res[prop][team][line] = outcome["oddsAmerican"]+"/"+outcomes[i+1]["oddsAmerican"]
				elif offerLabel.startswith("player's total"):
					line = str(outcome["line"] / 1000)
					res[prop][player] = {
						line: outcome["oddsAmerican"]+"/"+outcomes[i+1]["oddsAmerican"]
					}
				elif prop in ["superbowl", "conference", "division"]:
					team = convertTeam(outcome["participant"].lower())
					res[prop][team] = outcome["oddsAmerican"]
				else:
					try:
						last, first = outcome["participant"].lower().split(", ")
						player = parsePlayer(f"{first} {last}")
					except:
						player = parsePlayer(outcome["participant"])
					res[prop][player] = outcome["oddsAmerican"]

	with open("static/golf/kambi.json", "w") as fh:
		json.dump(res, fh, indent=4)

def writeCZ(token=None):
	base = "https://api.americanwagering.com/regions/us/locations/mi/brands/czr/sb/v4/sports/americanfootball/competitions/007d7c61-07a7-4e18-bb40-15104b6eac92/tabs/FUTURE_BETS%7CPlayer%20Futures"
	outfile = "outfuture"

	res = nested_dict()

	cookie = ""
	with open("token") as fh:
		cookie = fh.read()

	os.system(f"curl '{base}' --compressed -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0' -H 'Accept: */*' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br' -H 'Referer: https://sportsbook.caesars.com/' -H 'content-type: application/json' -H 'X-Unique-Device-Id: 8478f41a-e3db-46b4-ab46-1ac1a65ba18b' -H 'X-Platform: cordova-desktop' -H 'X-App-Version: 7.13.2' -H 'x-aws-waf-token: {cookie}' -H 'Origin: https://sportsbook.caesars.com' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: cross-site' -H 'TE: trailers' -o {outfile}")
	with open(outfile) as fh:
		data = json.load(fh)

	tabs = {}
	for j in data["secondaryTabs"]:
		prop = j["displayName"].lower()\
			.replace(" o|u", "")\
			.replace("season ", "")\
			.replace("tds", "td")\
			.replace("receiving", "rec")\
			.replace("yards", "yd")\
			.replace(" ", "_")
		tabs[prop] = j["id"]

	for prop, url in tabs.items():
		u = f"{base}/secondary/{url}"
		time.sleep(0.2)
		os.system(f"curl '{u}' --compressed -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0' -H 'Accept: */*' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br' -H 'Referer: https://sportsbook.caesars.com/' -H 'content-type: application/json' -H 'X-Unique-Device-Id: 8478f41a-e3db-46b4-ab46-1ac1a65ba18b' -H 'X-Platform: cordova-desktop' -H 'X-App-Version: 7.13.2' -H 'x-aws-waf-token: {cookie}' -H 'Origin: https://sportsbook.caesars.com' -H 'Connection: keep-alive' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: cross-site' -H 'TE: trailers' -o {outfile}")

		with open(outfile) as fh:
			data = json.load(fh)
		with open(outfile, "w") as fh:
			json.dump(data, fh, indent=4)

		for event in data["competitions"][0]["events"]:
			for market in event["keyMarketGroups"][0]["markets"]:
				if not market["display"]:
					continue

				line = str(market.get("line", ""))
				selections = market["selections"]
				skip = 2

				if prop in ["superbowl", "conference", "division", "mvp", "opoy", "dpoy", "oroy", "droy", "comeback"] or "most" in prop:
					skip = 1

				for i in range(0, len(selections), skip):
					try:
						ou = str(selections[i]["price"]["a"])
					except:
						continue
					if skip == 2:
						ou += f"/{selections[i+1]['price']['a']}"
						if selections[i]["name"].lower().replace("|", "") == "under":
							ou = f"{selections[i+1]['price']['a']}/{selections[i]['price']['a']}"

					if skip == 1:
						if prop in ["division", "conference", "superbowl"]:
							team = convertTeam(selections[i]["name"].replace("|", ""))
						else:
							team = parsePlayer(selections[i]["name"].replace("|", ""))
						res[prop][team] = ou
					elif "td" in prop or "yd" in prop or prop in ["sacks"]:
						#player = parsePlayer(event["name"].replace("|", "").split(" 2024")[0]).strip()
						player = parsePlayer(market["metadata"]["player"].replace("|", ""))
						res[prop][player][line] = ou
					else:
						team = convertTeam(event["name"].replace("|", ""))

						if prop in ["wins"]:
							res[prop][team][line] = ou
						else:
							res[prop][team] = ou


	with open("static/golf/cz.json", "w") as fh:
		json.dump(res, fh, indent=4)

def write365():

	js = """
	{
		function convertTeam(team) {
			team = team.toLowerCase();
			let t = team.replace(". ", "");
			if (team.split(" ")[0].length == 2) {
				t = team.split(" ")[0];
				if (["la", "ny"].includes(t)) {
					t = team.replace(" ", "").substring(0, 3);
				}
			} else {
				t = t.substring(0, 3);
			}
			if (t == "los") {
				if (team.includes("chargers")) {
					return "lac";
				}
				return "lar";
			} else if (t == "new") {
				if (team.includes("jets")) {
					return "nyj";
				} else if (team.includes("patriots")) {
					return "ne";
				} else if (team.includes("saints")) {
					return "no";
				}
				return "nyg";
			} else if (t == "tam") {
				return "tb";
			} else if (t == "kan") {
				return "kc";
			} else if (t == "jac") {
				return "jax";
			} else if (t == "gre") {
				return "gb";
			} else if (t == "san") {
				return "sf";
			} else if (t == "las") {
				return "lv";
			} else if (t == "arz") {
				return "ari";
			}
			return t;
		}

		function parsePlayer(player) {
			let p = player.toLowerCase().replaceAll(". ", " ").replaceAll(".", "").replaceAll("'", "").replaceAll("-", " ").replaceAll(" jr", "").replaceAll(" sr", "").replaceAll(" iii", "").replaceAll(" ii", "").replaceAll(" iv", "");
			if (p == "amon ra stbrown") {
				return "amon ra st brown"
			}
			return p;
		}

		async function main() {
			let data = {};
			for (el of document.querySelectorAll(".src-FixtureSubGroupWithShowMore_Closed")) {
				el.click();
				await new Promise(resolve => setTimeout(resolve, 10));
			}

			for (el of document.querySelectorAll(".msl-ShowMore_Link")) {
				if (el.innerText == "Show more") {
					el.click();
					await new Promise(resolve => setTimeout(resolve, 500));
				}
			}

			let prop = document.querySelector(".rcl-MarketGroupButton_MarketTitle").innerText.toLowerCase();

			let skip = 1;
			let isPlayer = false;
			if (prop == "to win outright") {
				prop = "superbowl";
			} else if (prop == "to win conference") {
				prop = "conference";
			} else if (prop == "to win division") {
				prop = "division";
			} else if (prop == "mvp") {
				prop = "mvp";
			} else if (prop == "regular season awards") {
				prop = "awards";

			} else if (prop == "regular season stat leaders") {
				prop = "leaders";
			} else if (prop == "regular season wins") {
				prop = "wins";
			} else if (prop == "to make the playoffs") {
				prop = "playoffs";
			} else if (prop.includes("player")) {
				prop = prop.split("player ")[1].split(" regular")[0].replace(" ", "_").replace("passing", "pass").replace("rushing", "rush").replace("receiving", "rec").replace("yards", "yd").replace("touchdowns", "td").replace("receptions", "rec").replace("defensive", "def").replace("interceptions", "int");
				if (prop == "regular_season int") {
					prop = "int";
				} else if (prop == "regular_season rec") {
					prop = "rec";
				}
				skip = 2;
				isPlayer = true;
			} else if (prop.includes("leaders")) {
				prop = "leaders";
			}

			let mainProp = prop;

			if (prop.includes("_yd") || prop == "wins" || prop == "playoffs") {
				data[prop] = {};
				let teams = [];
				for (let div of document.querySelectorAll(".srb-ParticipantLabel_Name")) {
					if (isPlayer) {
						teams.push(parsePlayer(div.innerText));
					} else {
						teams.push(convertTeam(div.innerText));
					}
				}
				let overs = [];
				let div = document.querySelectorAll(".gl-Market")[1];
				for (let overDiv of div.querySelectorAll(".gl-Participant_General")) {
					let spans = overDiv.querySelectorAll("span"); 
					if (spans.length == 1) {
						overs.push(spans[0].innerText);
					} else {
						overs.push(spans[1].innerText);
					}
				}
				div = document.querySelectorAll(".gl-Market")[2];
				let idx = 0;
				for (let underDiv of div.querySelectorAll(".gl-Participant_General")) {
					let spans = underDiv.querySelectorAll("span"); 
					if (spans.length == 1) {
						let odds = spans[0].innerText;
						data[prop][teams[idx]] = overs[idx]+"/"+odds;
					} else {
						let line = spans[0].innerText;
						let odds = spans[1].innerText;
						if (!data[prop][teams[idx]]) {
							data[prop][teams[idx]] = {};
						}
						data[prop][teams[idx]][line] = overs[idx]+"/"+odds;
					}
					idx += 1;
				}
			} else if (prop) {
				let player = "";
				for (let row of document.querySelectorAll(".gl-MarketGroupPod")) {

					if (row.innerText.includes("Others on Request")) {
						continue;
					}
					if (prop.includes("_td") || prop == "sacks" || prop == "int" || prop == "rec") {
						player = parsePlayer(row.querySelector(".src-FixtureSubGroupButton_Text").innerText);
					}

					if (mainProp == "leaders") {
						prop = row.querySelector(".src-FixtureSubGroupButton_Text").innerText.toLowerCase();
						if (prop.includes("scrimmage") || prop.includes("&") || prop.includes("qb with")) {
							continue;
						}
						prop = prop.split("season ")[1].split(" - ")[0].replace(" ", "_").replace("passing", "pass").replace("rushing", "rush").replace("receiving", "rec").replace("yards", "yd").replace("touchdowns", "td").replace("td's", "td").replace("receptions", "rec").replace("defensive", "def").replace("interceptions", "int").replace("_thrown", "");
						prop = "most_"+prop;
					} else if (mainProp == "awards") {
						prop = row.querySelector(".src-FixtureSubGroupButton_Text").innerText.toLowerCase();
						if (prop.includes("rookie of the year")) {
							if (prop.includes("offensive")) {
								prop = "oroy";
							} else {
								prop = "droy";
							}
						} else if (prop.includes("comeback")) {
							prop = "comeback";
						} else if (prop.includes("player of the year")) {
							if (prop.includes("offensive")) {
								prop = "opoy";
							} else {
								prop = "dpoy";
							}
						}
					}

					if (!data[prop]) {
						data[prop] = {};
					}

					let btns = row.querySelectorAll(".gl-Participant_General");
					for (let i = 0; i < btns.length; i += skip) {
						if (!btns[i].querySelector("span")) {
							continue;
						}
						let team = btns[i].querySelector("span").innerText;
						let odds = btns[i].querySelectorAll("span")[1].innerText;

						if (skip == 1) {
							if (["roty", "cy_young", "mvp"].includes(prop) || ["leaders", "awards"].includes(mainProp)) {
								data[prop][parsePlayer(team)] = odds;
							} else {
								data[prop][convertTeam(team)] = odds;
							}
						} else {
							let ou = odds;
							ou += "/"+btns[i+1].querySelectorAll("span")[1].innerText;
							if (team.indexOf("- No") >= 0) {
								ou = btns[i+1].querySelectorAll("span")[1].innerText+"/"+odds;
							}
							if (prop.includes("_td") || prop == "sacks" || prop == "int" || prop == "rec") {
								data[prop][player] = {};
								data[prop][player][team.split(" ")[1]] = ou;
							} else if (prop == "playoffs") {
								team = row.querySelector(".src-FixtureSubGroupButton_Text").innerText.toLowerCase().split(" to ")[0];
								data[prop][convertTeam(team)] = ou;
							} else {
								data[prop][parsePlayer(team.split(" - ")[0])] = ou;
							}
						}
					}
				}
			}
			console.log(data);
		}

		main();
	}
"""

def writeFanduelManual():

	js = """

	{
		function convertTeam(team) {
			team = team.toLowerCase();
			let t = team.replace(". ", "").substring(0, 3);
			if (t == "los") {
				if (team.includes("chargers")) {
					return "lac";
				}
				return "lar";
			} else if (t == "new") {
				if (team.includes("jets")) {
					return "nyj";
				} else if (team.includes("patriots")) {
					return "ne";
				} else if (team.includes("saints")) {
					return "no";
				}
				return "nyg";
			} else if (t == "tam") {
				return "tb";
			} else if (t == "kan") {
				return "kc";
			} else if (t == "jac") {
				return "jax";
			} else if (t == "gre") {
				return "gb";
			} else if (t == "san") {
				return "sf";
			} else if (t == "las") {
				return "lv";
			}
			return t;
		}

		function parsePlayer(player) {
			return player.toLowerCase().replaceAll(".", "").replaceAll("'", "").replaceAll("-", " ").replaceAll(" jr", "").replaceAll(" sr", "").replaceAll(" iii", "").replaceAll(" ii", "").replaceAll(" iv", "");
		}


		async function main() {
			const arrows = document.querySelectorAll("div[data-test-id='ArrowAction']");

			for (const arrow of arrows) {
				if (arrow.querySelector("svg[data-test-id=ArrowActionIcon]").querySelector("path").getAttribute("d").split(" ")[0] != "M.147") {
					arrow.click();
				}

				await new Promise(resolve => setTimeout(resolve, 0.1));
			}

			for (let el of document.querySelectorAll("div[aria-label='Show more']")) {
				if (el) {
					el.click();
					await new Promise(resolve => setTimeout(resolve, 0.1));
				}
			}

			let tab = document.querySelectorAll("div[aria-selected=true]")[0].innerText.toLowerCase();
			let btns = Array.from(document.querySelectorAll("ul")[5].querySelectorAll("div[role=button]"));
			for (let i = 0; i < btns.length; i += 1) {
				player = "";
				const btn = btns[i];
				let label = btn.getAttribute("aria-label");
				if (!label) {
					continue;
				}
				label = label.toLowerCase();
				if (label.includes("unavailable") || label[0] == ",") {
					continue;
				}

				let prop = "";

				if (["rookies", "conferences", "divisions", "season awards", "super bowl"].includes(tab) || (tab == "defensive props" && label.split(", ").length <= 2)) {
					let parent = btn.parentElement.parentElement.parentElement.parentElement.parentElement.parentElement.parentElement.parentElement;
					if (parent.nodeName != "LI") {
						continue;
					}
					while (parent.querySelector("h3[role=heading]") == null) {
						parent = parent.previousSibling;
					}
					prop = parent.querySelector("h3[role=heading]").innerText.toLowerCase();
					if (prop.includes("comeback")) {
						prop = "comeback";
					} else if (prop.includes("coach")) {
						if (prop.includes("assistant")) {
							continue;
						}
						prop = "coach";
					} else if (prop.includes("rookie of the year")) {
						if (prop.includes("offensive")) {
							prop = "oroy";
						} else {
							prop = "droy";
						}
					} else if (prop.includes("player of the year")) {
						if (prop.includes("offensive")) {
							prop = "opoy";
						} else {
							prop = "dpoy";
						}
					} else if (tab == "season awards" && prop.includes("mvp")) {
						if (prop.includes("parlay")) {
							continue;
						}
						prop = "mvp";
					} else if (prop.includes("championship winner")) {
						prop = "conference";
					} else if (tab == "divisions" && prop.includes("winner")) {
						prop = "division";
					} else if (prop.includes("most regular season sacks")) {
						prop = "most_sacks";
					} else if (tab == "super bowl" && prop.includes("outright")) {
						prop = "superbowl";
					} else {
						continue;
					}
				} else {
					prop = label.split(", ")[0];
					if (prop.includes("regular season total ")) {
						prop = label.split(", ")[0].split(" total ")[1].split(" 2024")[0].replace(" ", "_").replace("passing", "pass").replace("rushing", "rush").replace("receiving", "rec").replace("yards", "yd").replace("tds", "td").replace("receptions", "rec").replace("defensive", "def").replace("interceptions", "int");
						player = parsePlayer(label.split(" regular")[0].split(" 2024")[0]);
						i += 1;
					} else if (prop.includes("most regular season")) {
						prop = label.split(", ")[0].split(" season ")[1].split(" 2024")[0].replace(" ", "_").replace("passing", "pass").replace("rushing", "rush").replace("receiving", "rec").replace("yards", "yd").replace("tds", "td").replace("receptions", "rec").replace("defensive", "def").replace("interceptions", "int");
						prop = "most_"+prop;
						if (prop.includes("return")) {
							continue;
						}
					} else if (prop.includes(" - to make the playoffs")) {
						prop = "playoffs";
						i += 1;
					} else if (prop.includes("regular season wins")) {
						prop = "wins";
						i += 1;
					} else {
						continue;
					}
				}

				if (!data[prop]) {
					data[prop] = {};
				}

				if (player) {
					line = label.split(", ")[1].split(" ")[1];
					if (!data[prop][player]) {
						data[prop][player] = {};
					}
					data[prop][player][line] = label.split(", ")[2]+"/"+btns[i].getAttribute("aria-label").split(", ")[2];
				} else if (prop != "most_sacks" && prop.includes("most")) {
					player = parsePlayer(label.split(", ")[1]);
					data[prop][player] = label.split(", ")[2];
				} else if (prop == "playoffs") {
					team = convertTeam(label.split(" - ")[0]);
					data[prop][team] = label.split(", ")[2]+"/"+btns[i].getAttribute("aria-label").split(", ")[2];
				} else if (prop == "wins") {
					team = convertTeam(label.split(" regular ")[0].split(" - ")[0]);
					line = label.split(", ")[1].split(" ")[1];
					if (!data[prop][team]) {
						data[prop][team] = {};
					}
					data[prop][team][line] = label.split(", ")[2]+"/"+btns[i].getAttribute("aria-label").split(", ")[2];
				} else if (prop == "superbowl") {
					team = convertTeam(label.split(", ")[0]);
					data[prop][team] = label.split(", ")[1];
				} else if (["conference", "division"].includes(prop)) {
					player = convertTeam(label.split(", ")[0]);
					data[prop][player] = label.split(", ")[1];
				} else {
					player = parsePlayer(label.split(", ")[0]);
					data[prop][player] = label.split(", ")[1];
				}
			}

			console.log(data);
		}

		main();
	}

"""

def runThreads(book, totThreads=3):
	threads = tabs = []
	with open(f"static/golf/{book}.json", "w") as fh:
		json.dump({}, fh)
	for _ in range(totThreads):
		if book == "fd":
			thread = threading.Thread(target=runFD, args=())
			tabs = ["", "finishing-positions", "make-miss-cut", "round-score", "birdies-or-better", "matchups"]
			#tabs = ["matchups"]
		elif book == "mgm":
			thread = threading.Thread(target=runMGM, args=())
			tabs = ["2025-26-nfl-regular-season-stats-17265554"]
		thread.start()
		threads.append(thread)

	for tab in tabs:
		q.put(tab)
	q.join()

	for _ in range(totThreads):
		q.put(None)
	for thread in threads:
		thread.join()

def runFD():
	uc.loop().run_until_complete(writeFD())

async def writeFD():
	book = "fd"
	CURR_YEAR = datetime.now().year
	browser = await uc.start(no_sandbox=True)
	while True:
		data = nested_dict()
		tab = q.get()
		if tab is None:
			q.task_done()
			break

		url = f"https://sportsbook.fanduel.com/golf"
		if tab != "":
			url += f"?tab={tab}"
		page = await browser.get(url)
		try:
			await page.wait_for(selector="nav")
		except:
			q.task_done()
			continue

		arrows = await page.query_selector_all("div[data-testid=ArrowAction]")
		for arrowIdx, arrow in enumerate(arrows):
			prop = arrow.children[0].children[0].text.lower()

			if prop == "the open 2025":
				prop = "win"
			else:
				continue
			path = arrow.children[-1].children[0].children[0]
			if path.attributes[1].split(" ")[0] != "M.147":
				await arrow.click()

		mores = await page.query_selector_all("div[aria-label='Show more']")
		for more in mores[1:]:
			await more.click()

		btns = await page.query_selector_all("ul div[role=button]")
		matchupSeen = {}
		for btn in btns:
			if "aria-label" not in btn.attributes:
				continue
			labelIdx = btn.attributes.index("aria-label") + 1
			label = btn.attributes[labelIdx].lower()
			odds = label.split(" ")[-1]
			if label.startswith("tab ") or label.startswith("show ") or "unavailable" in label:
				continue

			if label.startswith("18 hole matchbet"):
				prop = "rd1_matchup"
				print(label.split(", ")[0].split("-")[-1].split(" vs "))
				a,h = map(str, label.split(", ")[0].split("-")[-1].split(" vs "))
				matchup = f"{parsePlayer(a)} v {parsePlayer(h)}".strip()
				player = parsePlayer(label.split(", ")[1])

				if matchup in matchupSeen:
					if matchup.startswith(player):
						data[prop][matchup] = odds+"/"+matchupSeen[matchup]
					else:
						data[prop][matchup] = matchupSeen[matchup]+"/"+odds
				else:
					matchupSeen[matchup] = odds
			elif label.startswith("round 1 score") or label.startswith("number of birdies"):
				if "birdies" in label:
					prop = "rd1_birdies+"
				else:
					prop = "rd1"

				player = parsePlayer(label.split(" - ")[-1].split(", ")[0])
				line = label.split(", ")[1].split(" ")[-1]
				if label.split(", ")[1].startswith("over "):
					if line in data[prop][player]:
						o = data[prop][player][line]
						data[prop][player][line] = odds+"/"+o.split("/")[-1]
					else:
						data[prop][player][line] = odds
				else:
					if line in data[prop][player]:
						data[prop][player][line] += "/"+odds
					else:
						data[prop][player][line] = "-/"+odds
			else:
				prop = convertProp(label.split(", ")[0])
				player = parsePlayer(label.split(", ")[1])

				data[prop][player] = odds


		if tab == "make-miss-cut":
			for player, over in data["make_cut"].items():
				#if "miss_cut"
				data["make_cut"][player] += "/"+data["miss_cut"][player]
			del data["miss_cut"]
		updateData(book, data)
		q.task_done()
	browser.stop()

def updateData(book, data):
	if data:
		with lock:
			file = f"static/golf/{book}.json"
			if os.path.exists(file):
				with open(file) as fh:
					d = json.load(fh)
			else:
				d = {}
			merge_dicts(d, data)
			with open(file, "w") as fh:
				json.dump(d, fh, indent=4)

def writeEV(propArg="", bookArg="fd", teamArg="", boost=None):
	if not boost:
		boost = 1

	with open(f"static/golf/fd.json") as fh:
		fdLines = json.load(fh)

	with open(f"static/golf/circa.json") as fh:
		circaLines = json.load(fh)

	lines = {
		#"kambi": kambiLines,
		#"mgm": mgmLines,
		"fd": fdLines,
		#"dk": dkLines,
		#"pn": pnLines,
		#"cz": czLines,
		"circa": circaLines,
		#"bet365": bet365Lines,
		#"espn": espnLines
	}

	with open("static/golf/ev.json") as fh:
		evData = json.load(fh)

	evData = {}

	props = {}
	for book in lines:
		for prop in lines[book]:
			props[prop] = 1

	for prop in props:
		if propArg and prop != propArg:
			continue
		handicaps = {}
		for book in lines:
			lineData = lines[book]
			if prop in lineData:
				if type(lineData[prop]) is not dict:
					handicaps[(" ", " ")] = ""
					break
				for handicap in lineData[prop]:
					player = playerHandicap = ""
					try:
						player = float(handicap)
						player = ""
						handicaps[(handicap, playerHandicap)] = player
					except:
						player = handicap
						playerHandicap = ""
						if type(lineData[prop][player]) is dict:
							for h in lineData[prop][player]:
								handicaps[(handicap, h)] = player
						elif type(lineData[prop][player]) is str:
							handicaps[(handicap, " ")] = player
						else:
							for h in lineData[prop][player]:
								handicaps[(handicap, " ")] = player

		for handicap, playerHandicap in handicaps:
			player = handicaps[(handicap, playerHandicap)]
			for i in range(2):
				highestOdds = []
				books = []
				odds = []

				for book in lines:
					lineData = lines[book]
					if prop in lineData:
						if type(lineData[prop]) is str:
							val = lineData[prop]
						else:
							if handicap not in lineData[prop]:
								continue
							val = lineData[prop][handicap]

						if player.strip():
							if type(val) is dict:
								if playerHandicap not in val:
									continue
								val = lineData[prop][handicap][playerHandicap]
							else:
								val = lineData[prop][handicap].split(" ")[-1]

						#if player == "ronald acuna":
						#	print(book, prop, player, val)
						try:
							o = val.split(" ")[-1].split("/")[i]
							ou = val.split(" ")[-1]
						except:
							if i == 1:
								continue
							o = val
							ou = val

						if not o or o == "-":
							continue

						try:
							highestOdds.append(int(o.replace("+", "")))
						except:
							continue

						odds.append(ou)
						books.append(book)

				if len(books) < 2:
					#print(player, prop, books, odds)
					continue

				removed = {}
				removedBooks = ["pn", "circa"]
				for book in removedBooks:
					#removed[book] = ""
					try:
						bookIdx = books.index(book)
						o = odds[bookIdx]
						#odds.remove(o)
						del odds[bookIdx]
						books.remove(book)
						removed[book] = o
					except:
						pass

				evBook = ""
				l = odds
				if bookArg:
					if bookArg not in books:
						continue
					evBook = bookArg
					idx = books.index(bookArg)
					maxOU = odds[idx]
					try:
						line = maxOU.split("/")[i]
					except:
						continue
				else:
					maxOdds = []
					for odds in l:
						try:
							maxOdds.append(int(odds.split("/")[i]))
						except:
							maxOdds.append(-10000)

					if not maxOdds:
						continue

					maxOdds = max(maxOdds)
					maxOU = ""
					for odds, book in zip(l, books):
						try:
							if str(int(odds.split("/")[i])) == str(maxOdds):
								evBook = book
								maxOU = odds
								break
						except:
							pass

					line = maxOdds

				line = convertAmericanOdds(1 + (convertDecOdds(int(line)) - 1) * boost)
				l.remove(maxOU)
				books.remove(evBook)

				for book in removed:
					books.append(book)
					l.append(removed[book])

				avgOver = []
				avgUnder = []
				for book in l:
					if book and book != "-":
						try:
							avgOver.append(convertDecOdds(int(book.split("/")[0])))
							if "/" in book:
								avgUnder.append(convertDecOdds(int(book.split("/")[1])))
						except:
							continue

				if avgOver:
					avgOver = float(sum(avgOver) / len(avgOver))
					avgOver = convertAmericanOdds(avgOver)
				else:
					avgOver = "-"
				if avgUnder:
					avgUnder = float(sum(avgUnder) / len(avgUnder))
					avgUnder = convertAmericanOdds(avgUnder)
				else:
					avgUnder = "-"

				if i == 1:
					ou = f"{avgUnder}/{avgOver}"
				else:
					ou = f"{avgOver}/{avgUnder}"

				if ou == "-/-" or ou.startswith("-/"):
					continue

				if ou.endswith("/-"):
					ou = ou.split("/")[0]
					
				key = f"{handicap} {playerHandicap} {prop} {'over' if i == 0 else 'under'}"
				if key in evData:
					continue

				j = {b: o for o, b in zip(l, books)}
				devig(evData, key, ou, line, prop=prop)

				if "circa" in books:
					o = j["circa"]
					if i == 1:
						o,u = map(str, j["circa"].split("/"))
						o = f"{u}/{o}"
					devig(evData, key, o, line, prop=prop, book="vs-circa")
				if key not in evData:
					continue
				implied = 0
				if line > 0:
					implied = 100 / (line + 100)
				else:
					implied = -1*line / (-1*line + 100)
				implied *= 100

				evData[key]["imp"] = round(implied)
				evData[key]["prop"] = prop
				evData[key]["book"] = evBook
				evData[key]["books"] = books
				evData[key]["ou"] = ou
				evData[key]["under"] = i == 1
				evData[key]["line"] = line
				evData[key]["fullLine"] = maxOU
				evData[key]["handicap"] = handicap
				evData[key]["playerHandicap"] = playerHandicap
				evData[key]["odds"] = l
				evData[key]["player"] = player
				j[evBook] = maxOU
				evData[key]["bookOdds"] = j

	with open("static/golf/ev.json", "w") as fh:
		json.dump(evData, fh, indent=4)

	with open(f"static/golf/evArr.json", "w") as fh:
		json.dump([value for key, value in evData.items()], fh)

def printEV():
	with open(f"static/golf/ev.json") as fh:
		evData = json.load(fh)

	data = []
	for player in evData:
		d = evData[player]
		j = [f"{k}:{d['bookOdds'][k]}" for k in d["bookOdds"] if k != d["book"]]
		data.append((d["ev"], player, d["playerHandicap"], d["line"], d["book"], j, d))

	for row in sorted(data):
		print(row[:-1])

	output = "\t".join(["EV", "EV Book", "Imp", "Player", "Prop", "O/U", "FD", "DK", "MGM", "CZ", "Kambi/BR", "PN", "Bet365", "ESPN"]) + "\n"
	for row in sorted(data, reverse=True):
		player = row[-1]["player"].title()
		if len(player) < 4:
			player = player.upper()
		prop = row[-1]["prop"]
		
		ou = ("u" if row[-1]["under"] else "o")+" "
		if player:
			ou += row[-1]["playerHandicap"]
		else:
			ou += row[-1]["handicap"]
		arr = [row[0], str(row[-1]["line"])+" "+row[-1]["book"].upper().replace("KAMBI", "BR").replace("BET", ""), f"{round(row[-1]['imp'])}%", player, row[-1]["prop"], ou]
		for book in ["fd", "dk", "mgm", "cz", "kambi", "pn", "bet365", "espn"]:
			o = str(row[-1]["bookOdds"].get(book, "-"))
			if o.startswith("+"):
				o = "'"+o
			arr.append(str(o))
		output += "\t".join([str(x) for x in arr])+"\n"

	with open("static/golf/props.csv", "w") as fh:
		fh.write(output)

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument("-d", "--date", help="date")
	parser.add_argument("--fd", action="store_true")
	parser.add_argument("--dk", action="store_true")
	parser.add_argument("--mgm", action="store_true", help="MGM")
	parser.add_argument("--kambi", action="store_true")
	parser.add_argument("--pn", action="store_true")
	parser.add_argument("--debug", action="store_true")
	parser.add_argument("--cz", action="store_true")
	parser.add_argument("--ev", action="store_true")
	parser.add_argument("--summary", action="store_true")
	parser.add_argument("-u", "--update", action="store_true")
	parser.add_argument("--boost", help="Boost", type=float)
	parser.add_argument("--book", help="Book")
	parser.add_argument("--token")
	parser.add_argument("--prop", help="Prop")
	parser.add_argument("--commit", "-c", action="store_true")
	parser.add_argument("-t", "--team", help="Team")
	parser.add_argument("-p", "--print", action="store_true", help="Print")
	parser.add_argument("--threads", type=int, default=3)

	args = parser.parse_args()

	if args.fd:
		runThreads("fd", totThreads=args.threads)

	if args.mgm:
		runThreads("mgm", totThreads=args.threads)

	if args.dk:
		writeDK(args.debug)

	if args.cz:
		uc.loop().run_until_complete(writeCZToken())
		writeCZ(args.token)

	if args.kambi:
		writeKambi()

	if args.pn:
		writePN(args.debug)

	if args.ev:
		writeEV(args.prop, args.book, args.team, args.boost)
	if args.print:
		printEV()

	if args.update:
		runThreads("fd", totThreads=args.threads)
		runThreads("mgm", totThreads=args.threads)
		writeDK(args.debug)
		uc.loop().run_until_complete(writeCZToken())
		writeCZ(args.token)
		writeKambi()
		writePN(args.debug)

	if args.summary:
		with open(f"static/golf/kambi.json") as fh:
			kambiLines = json.load(fh)

		with open(f"static/golf/mgm.json") as fh:
			mgmLines = json.load(fh)

		with open(f"static/golf/fd.json") as fh:
			fdLines = json.load(fh)

		with open(f"static/golf/dk.json") as fh:
			dkLines = json.load(fh)

		with open(f"static/golf/pn.json") as fh:
			pnLines = json.load(fh)

		with open(f"static/golf/cz.json") as fh:
			czLines = json.load(fh)

		with open(f"static/golf/bet365.json") as fh:
			bet365Lines = json.load(fh)

		with open(f"static/golf/circa.json") as fh:
			circaLines = json.load(fh)

		lines = {
			#"kambi": kambiLines,
			"mgm": mgmLines,
			"fd": fdLines,
			"cz": czLines,
			"dk": dkLines,
			"circa": circaLines,
			"pn": pnLines,
			"bet365": bet365Lines
		}

		for book in lines:
			for prop in lines[book]:
				if prop != args.prop:
					continue
				for team in lines[book][prop]:
					if team != args.team:
						continue

					print(f"{book} {lines[book][prop][team]}\n")

	if args.commit:
		commitChanges()