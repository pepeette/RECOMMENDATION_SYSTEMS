from taipy import Gui

page = """
<center><h2>Test **page**</h2></center>

<|layout|columns=1 1|
<|
Laetitia col 1 Hoquetis col 2
|>
|>



<|layout|columns= 2 1|
<|
<center> Top 10 Highest Total Suicides Per 100k Population Countries </center> 
<center> Part 1 from 2 1 </center> 
|>

<|
<center> Top 10 Countries vs. Rest of The World </center> 
<center> part 2 from 2 1 </center> 
|>

|>


<center>bottom</center>
"""

gui = Gui(page)
gui.run(dark_mode = False,port=5006)