# **Product Requirements Document (PRD)**

**Product:** Residential Solar & Battery Economic Simulation Model (Sweden)

**Version:** 1.1 (Battery Logic Phase 1)

**Subtitle:** Deterministic Baseline, Aggregator-Agnostic

## **Revision History**

| Version | Date | Description |
| :--- | :--- | :--- |
| 1.0 | 2026-04-16 | Initial baseline and solar physics definition. |
| 1.1 | 2026-04-19 | Refactored battery parameters into grouped `BatteryConfig`. Implemented FCR capacity allocation logic. |

## **1\. Objective**

Build a Python-based, hourly simulation model to assess the economic feasibility of residential solar PV and Battery Energy Storage Systems (BESS) in the Swedish market. The model will simulate 8,760 hours (one year) to calculate electrical flows and cash flows. It must support scenarios ranging from a "Do Nothing" baseline (no PV, no battery) to complex setups with multiple solar arrays and battery capacity dedicated to both self-consumption and Ancillary Services (e.g., FCR-D via aggregators like CheckWatt, Flower, or Varberg Energi).

The architecture must be explicitly designed as a fast, deterministic baseline that can be easily wrapped in a Monte Carlo (MC) simulation loop in future versions to model price and weather uncertainty.

## **2\. In Scope vs. Out of Scope**

### **What IS Included in V1:**

* **Hourly Resolution:** 8,760 steps per simulation run. The model assumes a standard non-leap year (exactly 8760 hours). Inputs with 8784 hours must be truncated or rejected.  
* **Vectorized Data:** Weather, prices, and load profiles processed as 1D arrays to maximize performance.  
* **Missing Components:** Ability to bypass PV (empty string list) or Battery capacity to 0 to calculate baselines.  
* **Multiple PV Arrays:** Support for several solar strings with different orientations (tilt/azimuth).  
* **Standard Load Profiling:** Approximation of hourly consumption curves from monthly aggregate data using a Standard Load Profile (SLP).  
* **Fixed FCR Allocation:** A static parameter defining the percentage of battery power reserved for Ancillary Services (FCR) vs. Self-consumption/Arbitrage.  
* **Grid Transfer Limits:** Constraints imposed by the physical size of the main property fuse (Amperes) on 3-phase 400V Swedish residential grids, correctly resulting in solar curtailment if export limits are exceeded.  
* **Swedish Market Economics:** Nord Pool Day-Ahead spot prices, FCR-D market prices, grid transfer fees, energy taxes, VAT, and the 60 öre/kWh "Skattereduktion" (tax credit for exported electricity).  
* **Aggregator Agnostic:** Generalized fee structures that support any aggregator.

### **What is NOT Included in V1:**

* **Dynamic Day-to-Day Optimization:** The battery will *not* dynamically switch between 100% FCR and 100% Arbitrage based on daily price forecasts. It will use the fixed allocation defined in the parameters.  
* **Battery Degradation:** Capacity fade or cycle-life degradation over multiple years is ignored; V1 is a single-year operational snapshot.  
* **Non-Linear Efficiencies:** Inverter and battery efficiencies are treated as constant (flat percentages), ignoring voltage-dependent or temperature-dependent efficiency curves.  
* **FCR-D Energy Penalties:** FCR operations are assumed to be ideal net-zero balancing over 24h. Energy penalties and thermal losses from real-world FCR-D activation are ignored.
* **Financing/CAPEX Costs:** V1 calculates *operational* cash flows and savings. It does not calculate NPV, loan amortization, or payback period.  
* **Phase Imbalance:** The model assumes perfectly symmetrical 3-phase loads and generation.

## **3\. System Architecture & MC Readiness Constraints**

The engineering agent must strictly adhere to the following to ensure future Monte Carlo compatibility:

1. **Vectorization First:** Use pandas and numpy. Avoid iterative for loops wherever possible.  
2. **Sequential Bottleneck:** The Battery State of Charge SOC(t) depends on SOC(t-1). This is the *only* component permitted to use a sequential loop (or numba for acceleration).  
3. **Stateless Functions:** Core logic modules (Solar Model, Financial Model) must be pure functions taking arrays and parameters as inputs, returning arrays as outputs.
4. **Performance SLA:** The core simulation loop must execute a full year (8,760 hours) in under 100 milliseconds on standard CPU hardware to ensure viability for 10,000+ iteration Monte Carlo runs.
5. **Data Alignment Integrity (Timezone/DST):** The data-loading layer must explicitly localize and assert that all 1D input arrays (Weather, Spot, FCR, Load) share identical timezone alignment (e.g., `Europe/Stockholm`) and correctly handle DST boundaries prior to execution.

## **4\. Inputs & Parameters (with Defaults)**

### **4.1. Geographical & Weather Inputs**

* **Location:** Latitude & Longitude (Default: 59.3293, 18.0686 for Stockholm).  
* **Weather Data:** Hourly GHI, DNI, DHI, and Temperature (Requires integration with pvlib using PVGIS or ERA5 data).

### **4.2. Solar PV Parameters**

Accepts a List of Dictionaries. If empty, PV logic is bypassed.

* capacity\_kw: DC Capacity in kWp (Default: 10.0).  
* tilt: Degrees from horizontal (Default: 35).  
* azimuth: Degrees, where 180 \= South in pvlib standard (Default: 180).  
* pr: Performance Ratio for system losses (Default: 0.80).

### **4.3. Battery Parameters**

If dictionary is missing/empty, Battery logic is bypassed.

* capacity\_kwh (E\_max): Total usable energy in kWh (Default: 10.0).  
* max\_power\_kw (P\_max): Inverter max power in kW (Default: 5.0).  
* round\_trip\_efficiency (eta\_rt): (Default: 0.90).  
* fcr\_allocation\_pct (FCR\_pct): Percentage of power dedicated to FCR markets (Default: 0.80). Must be strictly bounded `0.0 <= FCR_pct <= 1.0` (throw ValueError if out of bounds).

### **4.4. Load / Consumption Parameters**

* monthly\_kwh: List of 12 floats representing consumption per month (Jan-Dec).  
* slp\_weights: An array of length 8760 representing the normalized hourly weights of the Swedish Standard Load Profile (SLP).

### **4.5. Grid & Economic Market Parameters (SEK)**

* main\_fuse\_size\_a: Property main fuse size in Amperes (Default: 20).  
* price\_spot\_hourly: Array of 8760 Nord Pool Day-Ahead prices (SEK/kWh).  
* price\_fcr\_hourly: Array of 8760 FCR-D clearing prices (SEK/MW/h).  
* aggregator\_fee\_pct: Revenue cut taken by aggregator (Default: 0.20).  
* aggregator\_flat\_fee\_yearly: Flat annual subscription/hardware fee charged by the aggregator (Default: 0 SEK).
* grid_transfer_fee_sek: Variable grid transfer fee (Överföring) (Default: 0.18 SEK/kWh).
* energy_tax_sek: Statutory electricity tax (Energiskatt) (Default: 0.264 SEK/kWh).
* vat_rate: Value Added Tax (VAT/Moms) applied to energy components (Default: 0.25).
* utility\_sell\_compensation: Flat compensation from utility grid for sold electricity (Default: 0.05 SEK/kWh).

## **5\. Mathematical Models**

### **5.1. Maximum Grid Transfer Limit (Fuse Constraint)**

Calculate the maximum power (kW) that can be imported or exported based on the standard Swedish 3-phase 400V connection:

P\_grid\_max \= (main\_fuse\_size\_a \* 400 \* sqrt(3)) / 1000

### **5.2. Hourly Consumption Profiling**

Convert the 12 monthly\_kwh values (C\_m) into an 8760 array C(t) using the SLP weights W\_SLP(t). Where t in m means all hours t belonging to month m:

C(t) \= C\_m \* (W\_SLP(t) / sum(W\_SLP(t) for t in m))

### **5.3. Solar Production Model**

Using pvlib, calculate Plane of Array (POA) irradiance for each array i. Hourly AC output is:

P\_solar(t) \= sum(capacity\_kw\[i\] \* (I\_POA\[i\](t) / 1000\) \* pr\[i\])

Net load before battery:

Net(t) \= C(t) \- P\_solar(t)

### **5.4. Battery & Energy Management Logic**

The Battery is split into two virtual allocations: FCR and Arbitrage/Self-Consumption.

**FCR Reservation:**

Assumption: FCR operations maintain SOC around 50% and consume 0 net energy over a 24h period. The energy locked for this is assumed to be unavailable for arbitrage.

P\_FCR \= P\_max \* FCR\_pct

**Usable Arbitrage Capacity:**

P\_arb \= P\_max \- P\_FCR  
E\_arb \= E\_max \* (1 \- FCR\_pct)

**Linear Programming Optimizer (The Battery Loop):**

The battery schedule is optimized over the full 8760-hour horizon using a Linear Programming (LP) model with perfect foresight, mirroring modern Energy Management Systems (EMS) like Ferroamp or CheckWatt.

**Objective Function:**
Minimize total cost: Sum(Grid_buy(t) * Cost_buy(t) - Grid_sell(t) * Cost_sell(t))

**Variables per hour (t):**
* P_charge(t), P_discharge(t), SOC(t), Grid_buy(t), Grid_sell(t)

**Constraints:**
1. Power Balance: Grid_buy(t) - Grid_sell(t) - P_charge(t) + P_discharge(t) = Net(t)
2. SOC Update: SOC(t) = SOC(t-1) + (P_charge(t) * eta_c) - (P_discharge(t) / eta_d)
3. Bounds: 0 <= P_charge <= P_arb, 0 <= P_discharge <= P_arb, 0 <= SOC <= E_arb

### **5.5. Grid Balancing Layer (Vectorized Post-Loop)**

Let `Residual(t) = Net(t) + P_charge(t) - P_discharge(t)`
*(Note: Net is positive for load, negative for solar excess. P_charge adds demand, P_discharge reduces demand)*

**Where Residual(t) > 0 (Drawing from Grid):**
Grid\_buy(t) \= min(Residual(t), P\_grid\_max)
Unmet\_load(t) \= Residual(t) \- Grid\_buy(t)
Grid\_sell(t) \= 0
Curtailed(t) \= 0

**Where Residual(t) < 0 (Feeding to Grid):**
Grid\_sell(t) \= min(abs(Residual(t)), P\_grid\_max)
Curtailed(t) \= abs(Residual(t)) \- Grid\_sell(t)
Grid\_buy(t) \= 0
Unmet\_load(t) \= 0

### **5.6. Financial Model (Calculated Post-Loop)**

**Cash Flows (SEK):**

Spend(t) = Grid_buy(t) * ((price_spot_hourly(t) + grid_transfer_fee_sek + energy_tax_sek) * (1 + vat_rate))
  
Earn\_spot(t) \= Grid\_sell(t) \* (price\_spot\_hourly(t) \+ utility\_sell\_compensation)  
Rev\_FCR(t) \= (P\_FCR / 1000\) \* price\_fcr\_hourly(t) \* (1 \- aggregator\_fee\_pct)

**Post-Loop Tax Credit (Skattereduktion):**
*Note: The 60 öre tax rebate was dropped by the government and is no longer available. Tax credit calculations are removed from the model.*

## **6\. Output Requirements**

The model must output a results object/dictionary containing the metrics below. The function must accept a boolean flag (e.g., `return_timeseries=True`) which, if `False` during Monte Carlo iterations, skips returning the 8760-element daily/hourly arrays to aggressively conserve RAM, returning ONLY the global summaries.

### **6.1. Global Summaries (Yearly Totals)**

* total\_money\_spent\_sek: sum of Spend(t)  
* total\_money\_earned\_spot\_sek: sum of Earn\_spot(t)  
* total\_money\_earned\_fcr\_sek: sum of Rev\_FCR(t)  
* total\_curtailed\_solar\_kwh: sum of Curtailed(t)  
* total\_unmet\_load\_kwh: sum of Unmet\_load(t)
* net\_electricity\_cost\_sek: total\_money\_spent\_sek \- (total\_money\_earned\_spot\_sek \+ total\_money\_earned\_fcr\_sek) \+ aggregator\_flat\_fee\_yearly
* *(Optional but desired)*: Provide the net\_electricity\_cost\_sek of the baseline (0 PV, 0 Battery) to easily calculate annual savings.

### **6.2. Analytical Timeseries Data**

When `return_timeseries=True`, the model returns a Pandas DataFrame with 8,760 rows (hourly).

**Schema:**
* `consumption`: Hourly energy demand (kWh)
* `grid_buy`: Hourly energy imported from grid (kWh)
* `spot_prices`: Hourly Nord Pool spot price (SEK/kWh)
* `hourly_spend`: Hourly VAT-inclusive expenditure (SEK)
* `hourly_earn_spot`: Hourly revenue from grid export (SEK)

* solar\_irradiation\_kwh\_m2  
* solar\_power\_produced\_kwh  
* electricity\_consumed\_from\_grid\_kwh  
* electricity\_sold\_to\_grid\_kwh  
* money\_spent\_sek  
* money\_earned\_spot\_sek  
* money\_earned\_fcr\_sek  
* battery\_charged\_kwh  
* battery\_discharged\_kwh  
* curtailed\_solar\_kwh