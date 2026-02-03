from typing import List
from pydantic import BaseModel, Field


class HCPData(BaseModel):
    """Model for HCP demographic data from web search."""
    Name: List[str]
    address_line_1: List[str] = Field(..., alias="Address Line1")
    address_line_2: List[str] = Field(..., alias="Address Line2")
    First_Name: List[str] = Field(..., alias="First Name")
    Last_Name: List[str] = Field(..., alias="Last Name")
    Degree: List[str]
    NPI: List[str]
    ZIP: List[str]
    City: List[str]
    State: List[str]


class HCPAffiliationData(BaseModel):
    """Model for HCP affiliation data from web search."""
    NPI: List[str]
    HCO_ID: List[str]
    HCO_Name: List[str]
    HCO_Address1: List[str]
    HCO_City: List[str]
    HCO_State: List[str]
    HCO_ZIP: List[str]


class HCPSearchResponse(BaseModel):
    """Combined response model for HCP web search."""
    hcp_data: HCPData
    hcp_affiliation_data: HCPAffiliationData
