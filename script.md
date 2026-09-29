# 🛢️ PRAVAH (प्रवाह): The Baghewala Heavy Oil Digital Twin — Explained So Simply Even a Baby Can Understand

> **What is PRAVAH?**  
> **PRAVAH (प्रवाह)** means *"unbroken, continuous flow"*. It is the official name of our Smart India Hackathon (SIH 26120) project. It represents transforming frozen, immobile desert heavy crude into a smooth, optimized stream of oil and cash flow. Whether you are an oilfield executive, a college freshman, a hackathon judge, or a 10-year-old child, this guide explains what we built, why it matters, and how every piece of technology works.

---

## 🍯 Chapter 1: The Problem — Cold Honey Underground

Imagine you have a giant jar of honey.  
If it sits in the kitchen on a cold winter morning, what happens?  
It turns into thick, stiff goo. If you stick a straw into it and try to drink, **nothing comes out**, no matter how hard you suck.

That is the **Baghewala Heavy Oil Field** in Rajasthan, India, owned by Oil India Limited:
- There is **a huge ocean of oil** trapped 1,000 meters (over 3,000 feet) under the desert sand.
- But this oil is **heavy oil** (viscosity of ~15,000 centipoise at normal rock temperature).
- At underground temperature (40°C), it is **as thick as chilled peanut butter or asphalt**. It cannot flow through rocks, and it cannot flow up a pipe.

If you do nothing, that oil stays stuck underground forever.

---

## ♨️ Chapter 2: The Two Tools Engineers Use

To get the honey out of the jar, engineers do two things:

### 1. The Microwave Trick: CSS (Cyclic Steam Stimulation)
How do you make cold peanut butter runny? **You heat it up!**  
Engineers use a method called CSS, which works in 3 steps (the "Huff and Puff" cycle):
1. **INJECTION (The Blast):** They boil water on the surface and inject superheated steam (up to 300°C / 570°F) down into the rock for several days.
2. **SOAK (The Cook):** They shut the well and let the steam cook the rocks for 2 to 4 days. The oil temperature spikes from 40°C to over 240°C. Its thickness drops from 15,000 to just 10! It now flows like warm milk!
3. **PRODUCTION (The Sip):** They open the well and pump the hot, runny oil to the surface.

### 2. The Giant Syringe: The Sucker Rod Pump (SRP)
To lift the melted oil up from 1,000 meters deep, they use a "nodding donkey" pump (the horse-head pump you see bobbing up and down in movies).  
- On the surface, a motor rocks a beam up and down.
- Connected to that beam is a **steel metal rod string** that hangs down 1,000 meters into the ground.
- At the very bottom is a **plunger syringe with two one-way trapdoors** (valves).
- When the rod pulls up: it lifts oil to the surface.
- When the rod drops down: it sinks through the oil to get ready for the next scoop.

---

## 💥 Chapter 3: What Goes Wrong? (Why Oil Companies Lose Millions)

This seems simple on paper. But underground, it turns into a nightmare:

### 1. "The Rod Floating" Trap (Bending the 1-km Wire)
As production goes on, the rock cools down.  
As it cools, the oil turns back into thick tar!  
When the heavy steel rod tries to drop down through thick tar, **it can't sink fast enough**.  
The motor on the surface pushes down anyway, causing the 1,000-meter metal rod to **buckle, bend, scrape against the pipe walls, and snap in half**! Replacing a snapped rod string takes days and costs tens of thousands of dollars.

### 2. "The Fluid Pound" Hammer (Smashing the Pump)
If the pump moves too fast and scoops up oil faster than the rock can seep it in, the underground pump cylinder is only half-filled with oil and half-filled with empty vapor.  
When the plunger drops, it hits the liquid surface like a cannonball. This shockwave shatters valves and tears the pump apart.

### 3. "Going Broke on Steam" (The SOR Money Trap)
Steam is **not free**. To make steam, surface boilers burn natural gas.  
At the start of the production cycle, 1 ton of steam brings up 3 barrels of hot oil — you make big profits!  
Over the next two weeks, the rock cools down. Soon, you are using 1 ton of steam to get only 0.2 barrels of oil.  
If the steam costs $25 per ton, and a barrel of oil sells for $75, **every day you keep pumping after the breakeven point loses thousands of dollars**!

Oilfield managers often have to guess when to stop pumping and steam again. If they guess wrong, they burn millions in fuel.

---

## 🧠 Chapter 4: Our Solution — The "Digital Twin"

We built a **Digital Twin**.  
What is a digital twin?  
Think of it as a **live flight simulator for the entire oil field**.

Instead of guessing what is happening 1,000 meters underground, our software builds an exact mathematical and visual replica on a computer screen in real-time. It connects:
1. **The rocks & heat deep underground** (subsurface reservoir).
2. **The 1-kilometer bouncing steel rod and pump** (wellbore dynamics).
3. **The surface boilers, steam lines, and oil gathering pipes** (surface facility network).

---

## ⚡ Chapter 5: The 5 Superpowers Inside Our Digital Twin

Here are the 5 core brains that make our digital twin work:

### 1. 🧮 The Physics Brain (X-Ray Vision Through Rocks)
We don't have cameras 1,000 meters deep. So how do we know the oil's temperature?  
We programmed the true physics equations published in petroleum engineering:
- **Viscosity Math (Walther-ASTM):** Calculates oil thickness at any degree. At 40°C it's 14,900 cP; at 250°C it's 10 cP.
- **Boberg-Lantz Thermal Decline:** Calculates exactly how fast the underground rock loses its heat day by day.
- **Marx-Langenheim (1961):** Calculates the exact size and radius of the underground hot-steam bubble (e.g., 15,130 m² area, 69.4 meters wide).
- **Ramey Wellbore Heat Loss:** Calculates how much heat escapes as fluid travels 1 km up the pipe.

### 2. 🩺 The AI Doctor: Machine Learning Dynacard Reader
At the surface, a sensor measures the push and pull load on the rod as it moves.  
Plotting **Load vs. Position** creates a loop called a **Dynamometer Card (Dynacard)**.  
A Dynacard is literally an **EKG heart-monitor for an oil well**!
- A healthy pump makes a clean, full rectangle.
- A pump with rod floating sags at the top.
- A pump hitting fluid pound has a chunk bitten out of its bottom-right corner.
- A leaking valve makes the sides slant.

We trained an **AI Classifier (Random Forest)** on thousands of cards. Every single second, the AI reads the well's "heartbeat" and diagnoses:
- `Normal` (Running smoothly)
- `Rod Floating` (Danger! Oil is getting too thick)
- `Fluid Pound` (Danger! Chamber not filling)
- `Gas Interference` (Gas bubbles trapped)
- `Traveling Valve Leak` (Worn out valve seal)
- `Uncertain` (If confidence is below 70%, it honestly flags for human review)

### 3. 🏎️ The Smart Autopilot (VFD Advisory)
When you drive a car on an icy road, you don't slam the gas pedal — you slow down.  
Our system uses **Stokes Law of fluid physics**: it calculates the exact speed at which a steel rod can safely sink through oil of that specific viscosity.
- If the oil is hot and thin: the twin tells the motor, *"You can safely pump at 7 strokes per minute."*
- As the oil cools down: the twin automatically calculates the safe speed and warns the operator: *"Slow down to 3.8 strokes per minute to prevent the rod from bending!"*
- The operator can click one button on the dashboard to update the speed, or the twin can do it automatically over full-duplex WebSockets.

### 4. 💰 The Automated Accountant (The Breakeven Tracker)
Our twin continuously tracks the **Steam-Oil Ratio (SOR)**:
$$\text{Current SOR} = \frac{\text{Tons of Steam Used}}{\text{Barrels of Oil Produced}}$$

- It takes the live price of crude oil (e.g., \$75/barrel) and the cost of boiler steam (\$25/ton).
- Dividing \$75 by \$25 gives the **Economic Cutoff Limit: 3.0 t/bbl**.
- As long as SOR is below 3.0, you are printing money.
- The twin tracks both **Instantaneous SOR** and **Cycle Cumulative SOR**.
- Using a mathematical trend line (linear polyfit), it calculates an exact countdown: *"Warning: In 3 days, this well will cross the breakeven line and start losing money. Prepare boiler for re-steaming!"*

### 5. 🗺️ Mission Control (The SCADA Dashboard)
All of this information is displayed on an industrial-grade, dark-mode dashboard that looks like NASA mission control:
1. **Fleet Overview Page (`/`):** View all wells (`BGW-01`, `BGW-02`, `BGW-03`) at once. See who is making money, who is in soak, and who has an alert.
2. **Well Deep Dive (`/well/BGW-01`):** Watch the pump moving in real time. Switch between the Gibbs Dynacard and a vertical 2D cutaway diagram of the 1,200-meter wellbore.
3. **Surface Facility (`/surface`):** See the steam boilers, fuel gas consumption, and flowline pipelines to make sure oil doesn't freeze in the desert surface pipes.
4. **Historian & Economic Optimizer (`/analytics`):** Interactive graphs showing the Arps hyperbolic decline curve, where profit bars turn red the instant steam costs exceed oil revenues.

---

## 🔄 Chapter 6: A Day in the Life of a Well (Step-by-Step)

Here is what happens when you watch the digital twin run:

| Day | What Happens in the Physical World | What the Digital Twin Does |
|---|---|---|
| **Day 1–7** | **Steam Injection:** Boilers push 300°C steam into the rock. | Dashboard turns cyan: `INJECTION`. Marx-Langenheim engine calculates the steam radius expanding out to 69 meters. SRP pump is turned off. |
| **Day 8–9** | **Soak Period:** Well is closed. Heat cooks the reservoir. | Dashboard turns yellow: `SOAK`. Viscosity plunges from 15,000 cP down to 9 cP. |
| **Day 10** | **Production Starts:** SRP pump starts nodding. Hot oil floods up! | Dashboard turns green: `PRODUCTION`. Daily oil is 25+ bpd. Net margin is **+\$2,450/day**. Dynacard is a full, healthy rectangle. |
| **Day 16** | **Mid-Cycle Cooling:** Oil temperature declines from 250°C to 180°C. Viscosity rises to 60 cP. | AI detects the oil thickening. VFD advisory warns operator: *"Cap speed at 4.5 SPM to avoid rod buckling."* |
| **Day 21** | **Breakeven Cross:** Oil drops to 10 bpd. Instant SOR hits 3.16 t/bbl. Profit drops to zero. | Red alert flashes: `Transition to Injection (Economic Breakeven Surpassed)`. Automated transition is saved to SQLite database. The operator shuts the pump and starts the next steam cycle! |

**Result:** Zero broken rods, zero blown valves, and zero dollars wasted on unnecessary steam.

---

## 🏆 Chapter 7: Why This Wins (Judge & Technical FAQ)

If a judge or expert asks technical questions, here are the simple, unshakeable truths:

- **Q: Did you fake the data with random numbers?**  
  *Answer:* No. Every single curve is governed by real thermodynamic and fluid mechanics equations (Boberg-Lantz, Walther-ASTM, Stokes, and Arps hyperbolic decline) calibrated to real published literature on the Baghewala formation.
- **Q: Is the machine learning circular?**  
  *Answer:* No. The Random Forest model was evaluated on a completely independent test dataset generated with a different random seed and noise profile. It achieves 0.99 macro F1 score across 5 distinct fault classes, and its full evaluation report is committed in `ml/EVALUATION.md`.
- **Q: Is it really computing live?**  
  *Answer:* Yes! The backend computes live physics and streams full-duplex WebSocket frames at 1 Hz. It plays a 21-day CSS cycle compressed into 3 minutes so humans can witness multi-cycle degradation in a live demo without waiting 3 weeks.
- **Q: Does it have automated tests?**  
  *Answer:* Yes, 8 automated pytest cases verify viscosity at 3 temperatures (40°C, 100°C, 250°C), thermal decline, heated area expansion, Gibbs-lite transformation, and REST API token security.
- **Q: Can it run anywhere?**  
  *Answer:* Yes. The entire project is containerized with Docker and Docker Compose (`docker compose up`), requires zero hardcoded paths, and is licensed under the open-source MIT License.

---

### 🌟 In One Sentence:
> **Our Digital Twin is a real-time smart flight-simulator for heavy-oil wells that uses physics math and AI to prevent million-dollar equipment breakages and tell oilfield operators the exact moment to steam their wells for maximum profit.**
