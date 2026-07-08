import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const cwd = process.cwd();
const csvPath = path.join(cwd, "data", "scenario_training_master.csv");
const outputDir = path.join(cwd, "outputs");
await fs.mkdir(outputDir, { recursive: true });

const csvText = await fs.readFile(csvPath, "utf8");
const workbook = await Workbook.fromCSV(csvText, { sheetName: "Scenario Training Master" });
const sheet = workbook.worksheets.getItem("Scenario Training Master");

sheet.showGridLines = false;
sheet.freezePanes.freezeRows(1);
sheet.getUsedRange().format = {
  font: { name: "Aptos", size: 10 },
  wrapText: true,
  verticalAlignment: "top",
};
sheet.getRange("A1:G1").format = {
  fill: "#1F4E79",
  font: { bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "middle",
  wrapText: true,
};
sheet.getRange("A1:G101").format.borders = {
  preset: "all",
  style: "thin",
  color: "#D9E2F3",
};
sheet.getRange("A:A").format.columnWidthPx = 520;
sheet.getRange("B:B").format.columnWidthPx = 110;
sheet.getRange("C:C").format.columnWidthPx = 105;
sheet.getRange("D:D").format.columnWidthPx = 100;
sheet.getRange("E:E").format.columnWidthPx = 120;
sheet.getRange("F:F").format.columnWidthPx = 120;
sheet.getRange("G:G").format.columnWidthPx = 210;
sheet.getRange("A1:G101").format.rowHeightPx = 36;
sheet.getRange("A1:G1").format.rowHeightPx = 42;
sheet.tables.add("A1:G101", true, "ScenarioTrainingMaster");

const summary = workbook.worksheets.add("Summary");
summary.showGridLines = false;
summary.getRange("A1:D1").values = [["Scenario Training Master", "", "", ""]];
summary.getRange("A1:D1").merge();
summary.getRange("A1:D1").format = {
  fill: "#1F4E79",
  font: { bold: true, color: "#FFFFFF", size: 14 },
  horizontalAlignment: "center",
};
summary.getRange("A3:B8").values = [
  ["Total scenarios", 100],
  ["Car rental", 25],
  ["Hotel", 25],
  ["Restaurant", 25],
  ["Healthcare", 25],
  ["Required columns filled", "Yes"],
];
summary.getRange("A3:B8").format.borders = {
  preset: "all",
  style: "thin",
  color: "#D9E2F3",
};
summary.getRange("A3:A8").format = {
  fill: "#EAF2F8",
  font: { bold: true },
};
summary.getRange("A:A").format.columnWidthPx = 220;
summary.getRange("B:B").format.columnWidthPx = 160;
summary.getRange("A10:D10").values = [["How to use", "", "", ""]];
summary.getRange("A10:D10").merge();
summary.getRange("A10:D10").format = {
  fill: "#D9EAF7",
  font: { bold: true },
};
summary.getRange("A11:D14").values = [
  ["Edit data/scenario_training_master.csv as the source of truth.", "", "", ""],
  ["Keep scenario_text, domain, channel, intent, journey_stage, tapl_action, and expected_candidate_id populated.", "", "", ""],
  ["Run .\\.venv\\Scripts\\python.exe scripts\\train_all_models.py", "", "", ""],
  ["The trainer regenerates data/generated/*.csv and saves models/*.joblib.", "", "", ""],
];
summary.getRange("A11:D14").merge(true);
summary.getRange("A11:D14").format = {
  wrapText: true,
  verticalAlignment: "top",
};
summary.getRange("A11:D14").format.borders = {
  preset: "all",
  style: "thin",
  color: "#D9E2F3",
};
summary.getRange("A11:D14").format.rowHeightPx = 32;

const preview = await workbook.render({
  sheetName: "Scenario Training Master",
  range: "A1:G18",
  scale: 1,
  format: "png",
});
await fs.writeFile(
  path.join(outputDir, "scenario_training_master_preview.png"),
  new Uint8Array(await preview.arrayBuffer()),
);

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(path.join(outputDir, "scenario_training_master.xlsx"));
