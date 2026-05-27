# Research Report: volume profile point of control auction market profile trading

**Notebook**: Research 2026-05-17 17:42
**Sources**: 2
**Generated**: 2026-05-17 17:43
**Duration**: 43.7s

---

# Comprehensive Study Guide: Auction Theory, Market Profile, and Trading

This study guide synthesizes the fundamental principles of auction theory and the technical application of Market Profile charting. It is designed to provide a deep understanding of how markets facilitate trade, the historical evolution of bidding processes, and the statistical methodologies used by traders to identify value.

---

## I. Core Concepts and Thematic Analysis

### 1. The Auction Process and Theory
An auction is a process of buying and selling goods or services by offering them for bids. In a **forward auction**, the seller expects the highest price from multiple buyers. In a **reverse auction**, the roles are flipped: multiple sellers compete to offer the lowest price to a single buyer.

**Key Auction Formats:**
*   **English Auction (Open Ascending):** The most common type. Participants bid openly, each bid higher than the last, until no further bids are made.
*   **Dutch Auction (Open Descending):** The auctioneer starts with a high price and lowers it until a bidder accepts the current price.
*   **Sealed-Bid Auctions:** Bidders submit bids simultaneously without knowing others' offers. In a **First-Price** version, the winner pays their bid. In a **Vickrey (Second-Price)** version, the winner pays the amount of the second-highest bid.
*   **Double Auction:** Takes bids from both buyers and sellers simultaneously. A **Walrasian auction** is a specific type where the auctioneer adjusts prices until supply and demand perfectly balance.

### 2. Market Profile Mechanics
Devised by J. Peter Steidlmayer at the Chicago Board of Trade (CBOT), Market Profile is an intra-day charting technique that organizes price and time data to identify market value. It typically follows a **Gaussian (normal) distribution**, resulting in a bell-shaped curve.

*   **Time-Price Opportunity (TPO):** The basic unit of a Market Profile, representing the occurrence of a price at a specific time (often designated by letters).
*   **Point of Control (POC):** The price level where the most trading activity (or volume) occurred during the day. It represents the "fairest" price at which the most trade was facilitated.
*   **Value Area:** The price range representing the central 70% of the day’s trading activity (roughly one standard deviation from the POC).
*   **Initial Balance:** The price range established during the first hour of the trading day.

### 3. Market Distribution and Equilibrium
The validity of Market Profile analysis relies on the market being in a state of **equilibrium**. 
*   **Normal Distribution:** Activity is concentrated in the middle (POC) and trails off at extreme highs and lows.
*   **Steidlmayer Distribution:** Describes the transition as a market moves out of equilibrium into a new trend.
*   **Limitations:** If a market is trending aggressively or lacks a normal distribution, POC and Value Area calculations may be misleading.

---

## II. Short-Answer Practice Questions

**1. What is the etymological origin of the word "auction"?**
The word is derived from the Latin *auctus*, the past participle of *augeō*, meaning "I increase."

**2. Explain the difference between a "reserve auction" and a "no-reserve auction."**
In a reserve auction, the seller reserves the right to reject the highest bid if it does not meet a predetermined minimum price. In a no-reserve (or absolute) auction, the item is sold to the highest bidder regardless of the final price.

**3. What is "auction sniping" and how do some platforms prevent it?**
Sniping is the practice of placing a bid at the very last moment of a timed auction to prevent others from responding. Platforms prevent this using "soft closes" or "dynamic closing," which extends the auction time if a bid is placed near the end.

**4. How does a "Vickrey auction" differ from a standard "first-price sealed-bid auction"?**
In both, bids are hidden. However, in a Vickrey auction, the winner pays the price of the *second-highest* bid rather than their own, which is intended to encourage bidders to bid their true valuation.

**5. Define the "Initial Balance" in Market Profile trading.**
The Initial Balance is the price range and location established during the first hour of trading. It is used to identify "Day Types" and determine which type of trader (short-term or long-term) is in control.

**6. What is the primary difference between a Market Profile and a Volume Profile?**
Market Profile organizes price activity in relation to time (using TPOs), whereas Volume Profile is based purely on price and the actual volume traded at those prices, ignoring the time spent at each level.

**7. Describe "chandelier bidding."**
This is an auctioneer tactic (common in high-end art) of calling out false bids—often by looking at a spot in the room like a chandelier—to create the appearance of demand and increase momentum toward the reserve price.

---

## III. Essay Prompts for Deeper Exploration

1.  **The Evolution of Auction Contexts:** Analyze the shift from historical "human commodity" auctions (such as Roman slave auctions and Babylonian marriage markets) to modern "digital goods" auctions (like CryptoKitties and online advertising slots). How has the emergence of the internet altered auction theory and participant anonymity?
2.  **Market Profile and the Gaussian Assumption:** Market Profile analysis is fundamentally based on the Gaussian (normal) distribution. Discuss the risks and limitations of applying this statistical model to financial markets, particularly during "trend days" or periods of non-equilibrium.
3.  **Bidding Strategies and the Winner's Curse:** Compare the strategies of "bid shading" and "jump bidding." How do these tactics relate to the "winner's curse," and what role does information asymmetry play in the final hammer price?
4.  **The Economic Significance of Spectrum Auctions:** Governments often use auctions to sell radio spectrum licenses and debt obligations. Evaluate the social and economic impact of these "high-revenue" auctions compared to private-item auctions.

---

## IV. Glossary of Important Terms

| Term | Definition |
| :--- | :--- |
| **Absentee Bid** | A bid submitted by a buyer who is not physically present, also known as a commission bid. |
| **Auction Block** | The raised platform where the auctioneer stands; also used as slang for the auction itself. |
| **Bid Rigging (Collusion)** | An illegal practice where bidders form a "ring" to manipulate the auction results and keep prices low. |
| **Buyout Price** | A set price that, if accepted, immediately ends the auction (e.g., eBay's "Buy It Now"). |
| **Calor Licitantis** | Also known as "auction fever," describing irrational bidding behavior caused by high emotions. |
| **Chandelier Bidding** | The practice of an auctioneer raising false bids to create an appearance of demand. |
| **Double Auction** | An auction where both buyers and sellers submit bids simultaneously (e.g., stock exchanges). |
| **Hammer Price** | The final price at which a lot is sold, excluding premiums and taxes. |
| **Increment** | The minimum amount by which a new bid must exceed the previous one. |
| **Initial Balance** | The price range established during the first hour of a trading day in Market Profile. |
| **Lot** | An individual item or group of items being sold as a single unit. |
| **Point of Control (POC)** | The price level in Market Profile with the highest concentration of trading activity. |
| **Proxy Bid** | A bid placed by an authorized representative or automated system on behalf of an absent bidder. |
| **TPO (Time-Price Opportunity)** | A marker in Market Profile indicating that a price was reached during a specific time period. |
| **Value Area** | The price range where 70% of the day's trading activity occurs, centered around the POC. |
| **Winner's Curse** | A situation where the winner of an auction pays more for an item than its actual value due to overestimation. |
| **Yankee Auction** | A single-attribute multiunit auction where bidders bid on portions of a total amount of identical units. |

---

## V. Historical Landmarks in Auction History

*   **500 BC:** Earliest recorded auctions in Babylon (Marriage Markets).
*   **193 AD:** The Praetorian Guard put the entire Roman Empire on the auction block; won by Didius Julianus.
*   **1674:** Stockholm Auction House (*Stockholms Auktionsverk*), the world's first auction house, is founded.
*   **1744 / 1766:** Foundations of Sotheby’s and Christie’s, respectively, in London.
*   **1985:** Market Profile is introduced to the public via the CBOT.
*   **2017:** Leonardo da Vinci’s *Salvator Mundi* sells for $450.3 million, the most expensive item ever sold at auction.
*   **2020:** Paul Milgrom and Robert B. Wilson receive the Nobel Prize for improvements to auction theory.

---

## Sources

[1] Auction - Wikipedia — <https://en.wikipedia.org/wiki/Auction>
[2] Market profile - Wikipedia — <https://en.wikipedia.org/wiki/Market_profile>
