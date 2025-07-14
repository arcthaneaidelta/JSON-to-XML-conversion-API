from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import Response
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="JSON to XML Converter API",
    description="Convert JSON binary files to XML binary files",
    version="1.0.0"
)

class JsonToXmlConverter:
    """Utility class for converting JSON to XML"""
    
    @staticmethod
    def dict_to_xml(data, root_name="root"):
        """Convert a dictionary to XML element"""
        def build_xml_element(parent, key, value):
            """Recursively build XML elements"""
            if isinstance(value, dict):
                # Create element for dictionary
                element = ET.SubElement(parent, str(key))
                for k, v in value.items():
                    build_xml_element(element, k, v)
            elif isinstance(value, list):
                # Handle lists
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        # Create element for each dictionary in list
                        list_element = ET.SubElement(parent, str(key))
                        for k, v in item.items():
                            build_xml_element(list_element, k, v)
                    else:
                        # Create element for each primitive in list
                        list_element = ET.SubElement(parent, str(key))
                        list_element.text = str(item)
            else:
                # Handle primitive values
                element = ET.SubElement(parent, str(key))
                element.text = str(value) if value is not None else ""
        
        # Create root element
        root = ET.Element(root_name)
        
        if isinstance(data, dict):
            for key, value in data.items():
                build_xml_element(root, key, value)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                build_xml_element(root, f"item_{i}", item)
        else:
            root.text = str(data)
        
        return root
    
    @staticmethod
    def prettify_xml(element):
        """Return a pretty-printed XML string"""
        rough_string = ET.tostring(element, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    @staticmethod
    def convert_json_to_xml(json_content: str, root_name: str = "root") -> str:
        """Convert JSON string to XML string"""
        try:
            # Parse JSON
            data = json.loads(json_content)
            
            # Convert to XML
            xml_element = JsonToXmlConverter.dict_to_xml(data, root_name)
            
            # Pretty print XML
            xml_string = JsonToXmlConverter.prettify_xml(xml_element)
            
            return xml_string
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid JSON format: {e}")
        except Exception as e:
            logger.error(f"XML conversion error: {e}")
            raise HTTPException(status_code=500, detail=f"Error converting JSON to XML: {e}")

@app.post("/convert-json-to-xml")
async def convert_json_to_xml(
    file: UploadFile = File(...),
    root_element: str = "root"
):
    """
    Convert JSON binary file to XML binary file
    
    Args:
        file: JSON binary file to convert
        root_element: Name of the root XML element (default: "root")
    
    Returns:
        XML file as binary response
    """
    # Validate file type
    if not file.filename.lower().endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")
    
    if file.content_type and file.content_type not in ['application/json', 'text/json', 'application/octet-stream']:
        logger.warning(f"Unexpected content type: {file.content_type}")
    
    try:
        # Read file content
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        # Decode JSON content
        try:
            json_content = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                json_content = content.decode('utf-8-sig')  # Try with BOM
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="Invalid file encoding. Please use UTF-8 encoded JSON file")
        
        # Convert JSON to XML
        xml_content = JsonToXmlConverter.convert_json_to_xml(json_content, root_element)
        
        # Generate output filename
        base_filename = file.filename.rsplit('.', 1)[0]
        xml_filename = f"{base_filename}.xml"
        
        # Return XML as binary response
        return Response(
            content=xml_content.encode('utf-8'),
            media_type="application/xml",
            headers={
                "Content-Disposition": f"attachment; filename={xml_filename}",
                "Content-Type": "application/xml; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in convert_json_to_xml: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "JSON to XML Converter API",
        "version": "1.0.0",
        "endpoint": "/convert-json-to-xml",
        "description": "Convert JSON binary files to XML binary files",
        "usage": "POST /convert-json-to-xml with JSON file in form-data"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "service": "JSON to XML Converter"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
