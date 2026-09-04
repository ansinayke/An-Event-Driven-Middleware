from fastapi import FastAPI, Request, Response
import xml.etree.ElementTree as ET
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="CMS Mock Service - SOAP API")

@app.post("/soap/order")
async def process_order(request: Request):
    body = await request.body()
    logger.info(f"CMS Mock received SOAP request: {body.decode()}")
    
    # Simple XML parsing to extract order_id
    try:
        root = ET.fromstring(body)
        # Assuming namespace or structure: Envelope -> Body -> ProcessOrder -> OrderId
        # We will do a simple find for testing purposes
        order_id_elem = None
        for elem in root.iter():
            if 'OrderId' in elem.tag:
                order_id_elem = elem
                break
                
        order_id = order_id_elem.text if order_id_elem is not None and order_id_elem.text is not None else "unknown"
    except Exception as e:
        logger.error(f"Failed to parse XML: {e}")
        order_id = "unknown"

    logger.info(f"CMS Mock processing order: {order_id}")
    
    # Simulate business logic failure for specific order ids (e.g. ends with 999)
    if order_id.endswith("999"):
        success = "false"
        reason = "CMS rejected order (simulated)"
    else:
        success = "true"
        reason = ""

    # Generate SOAP XML Response
    soap_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
   <soapenv:Body>
      <ProcessOrderResponse>
         <Success>{success}</Success>
         <Reason>{reason}</Reason>
      </ProcessOrderResponse>
   </soapenv:Body>
</soapenv:Envelope>"""

    return Response(content=soap_response, media_type="application/xml")

@app.get("/health")
async def health():
    return {"status": "ok"}
