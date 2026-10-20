# Technical sources and provenance

Reviewed 2026-10-20 UTC for this engineering alpha. These are technical implementation references, not validation of physiological interpretations.

- Garmin, [FIT protocol](https://developer.garmin.com/fit/protocol/), [activity file types](https://developer.garmin.com/fit/articles/file-types/activity.html), [encoding recipe](https://developer.garmin.com/fit/articles/cookbook/encoding_activity_files.html), [decoding recipe](https://developer.garmin.com/fit/articles/cookbook/decoding_activity_files.html).
- fitdecode maintainers, [reader API](https://fitdecode.readthedocs.io/en/latest/reference/reader.html) and [source](https://github.com/polyvertex/fitdecode). This implementation uses fitdecode 0.11.x and its installed FIT profile for field units/scales/enums.
- Garmin, [TCX schema endpoint](https://www8.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd) and [ActivityExtension schema endpoint](https://www8.garmin.com/xmlschemas/ActivityExtensionv2.xsd). These endpoints were not retrievable through the research browser in this session; the importer is intentionally limited to documented conventional fields and tested original fixtures, not claimed to be fully XSD-validated.
- Topografix, [GPX 1.1 schema documentation](https://www.topografix.com/GPX/1/1/). GPX SI/WGS84 conventions and timed track segments.
- Open-Meteo, [historical weather API](https://open-meteo.com/en/docs/historical-weather-api) and [official OpenAPI schema](https://github.com/open-meteo/open-meteo/blob/main/openapi/historical-weather.yml). ERA5 is requested explicitly; units and returned grid/time matches are checked. Review current service terms for your deployment; free API entitlement is not assumed for paid coaching services.
- Model Context Protocol, [official Python SDK](https://github.com/modelcontextprotocol/python-sdk) and [v1 documentation](https://py.sdk.modelcontextprotocol.io/v1/). This alpha uses MCP v1 FastMCP stdio and a real client/server protocol test.

## Data inventory

All committed examples and generated benchmark files are original synthetic data. No athlete records, third-party workout files or credentials were committed. The FIT fixture is encoded by this project with known field values and valid CRC; it is not an actual watch export. Tests do not establish compatibility with compressed/developer-field/export variants beyond the decoder and explicitly mapped fields.

The live weather smoke test used only the synthetic route/date, never an athlete location. Retrieved weather is attributed to Open-Meteo and ECMWF/Copernicus under the provider's applicable attribution terms. Live response caches are local test outputs, not bundled source data. Unit-test weather responses are invented and labeled synthetic. Third-party libraries retain their own licenses.
