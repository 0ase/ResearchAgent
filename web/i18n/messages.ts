import enCommon from "@/messages/en/common.json";
import enNavigation from "@/messages/en/navigation.json";
import enComposer from "@/messages/en/composer.json";
import enTask from "@/messages/en/task.json";
import enReport from "@/messages/en/report.json";
import enEvidence from "@/messages/en/evidence.json";
import enPapers from "@/messages/en/papers.json";
import enHistory from "@/messages/en/history.json";
import enReplay from "@/messages/en/replay.json";
import enSettings from "@/messages/en/settings.json";
import enPet from "@/messages/en/pet.json";
import zhCommon from "@/messages/zh-CN/common.json";
import zhNavigation from "@/messages/zh-CN/navigation.json";
import zhComposer from "@/messages/zh-CN/composer.json";
import zhTask from "@/messages/zh-CN/task.json";
import zhReport from "@/messages/zh-CN/report.json";
import zhEvidence from "@/messages/zh-CN/evidence.json";
import zhPapers from "@/messages/zh-CN/papers.json";
import zhHistory from "@/messages/zh-CN/history.json";
import zhReplay from "@/messages/zh-CN/replay.json";
import zhSettings from "@/messages/zh-CN/settings.json";
import zhPet from "@/messages/zh-CN/pet.json";

const zhMessages = {
  common: zhCommon,
  navigation: zhNavigation,
  composer: zhComposer,
  task: zhTask,
  report: zhReport,
  evidence: zhEvidence,
  papers: zhPapers,
  history: zhHistory,
  replay: zhReplay,
  settings: zhSettings,
  pet: zhPet,
};

const enMessages = {
  common: enCommon,
  navigation: enNavigation,
  composer: enComposer,
  task: enTask,
  report: enReport,
  evidence: enEvidence,
  papers: enPapers,
  history: enHistory,
  replay: enReplay,
  settings: enSettings,
  pet: enPet,
};

export type AppMessages = typeof zhMessages;

export function getMessages(locale: "zh-CN" | "en"): AppMessages {
  return locale === "zh-CN" ? zhMessages : enMessages;
}
