from typing import List
from pydantic import BaseModel, Field


class HCOData(BaseModel):
    """Model for HCO demographic data from web search."""
    Name: List[str]
    address_line_1: List[str] = Field(..., alias="Address Line1")
    address_line_2: List[str] = Field(..., alias="Address Line2")
    ZIP: List[str]
    City: List[str]
    State: List[str]
    Country: List[str]


class HCOAffiliationData(BaseModel):
    """Model for HCO affiliation data from web search."""
    HCO_ID: List[str]
    HCO_Name: List[str]
    HCO_Address1: List[str]
    HCO_City: List[str]
    HCO_State: List[str]
    HCO_ZIP: List[str]


class HCOSearchResponse(BaseModel):
    """Combined response model for HCO web search."""
    hco_data: HCOData
    hco_affiliation_data: HCOAffiliationData
