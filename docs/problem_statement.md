# Problem statement

## Scenario

A hypothetical independent coffee shop owner wants to open a new shop in Southampton. The target customers are young professionals, so the owner wants neighbourhoods with many residents aged 25 to 34. The owner also wants to stay at least one mile away from every existing Starbucks to avoid direct competition.

This is a teaching scenario. No real business is involved.

## Question

Which Southampton neighbourhoods have a high share of residents aged 25 to 34 and most of their land more than one mile from every Starbucks?

## Definitions

| Term | Definition |
|---|---|
| Neighbourhood | Lower layer Super Output Area (LSOA), 2021 boundaries. There are 152 in Southampton |
| Share aged 25 to 34 | Residents aged 25 to 29 plus 30 to 34, divided by all residents (Census 2021, table TS007A) |
| High | Top quartile of that share across all 152 Southampton LSOAs. The cut off is 17.89% |
| Exclusion zone | The union of 1 mile (1609.34 m) circles around each Starbucks, calculated in British National Grid (EPSG:27700) |
| Candidate | A high share LSOA with at least 50% of its land outside the exclusion zone |
| Borderline | A candidate with a share within 0.5 points of the cut off or under 60% of its land outside the zone |

## Inputs

1. Census 2021 age by five year bands, LSOA level (Nomis, Office for National Statistics)
2. LSOA December 2021 boundaries (ONS Open Geography Portal)
3. Four Starbucks locations, identified manually in Google Maps

## Outputs

1. A ranked table of 12 candidate neighbourhoods (`outputs/tables/final_shortlist.csv`)
2. A static map with a continuous colour scale for the share aged 25 to 34 (`MAPS/final_map_1mile.png`)
3. An interactive dashboard on OpenStreetMap, Esri streets or satellite tiles (`outputs/southampton_coffee_dashboard.html`)

## Method

All spatial operations use terrio v0.5.0: `buffer`, `dissolve` and `overlay` (intersection and difference). Python handles the table join and the plots only.

## Out of scope

Competitors other than Starbucks, rents, footfall, walking routes and planning rules.
