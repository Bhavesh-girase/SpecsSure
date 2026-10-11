// Site map — one place that describes every page, so the menu, breadcrumbs and footer stay in sync.
// Each page carries a plain-language line that says what you can do there.
import {
  BookOpen, Briefcase, FilePlus2, FileSearch, Gauge, Info, Link2, Network, Puzzle, Radar,
  Search, Store, UserCog, Wrench, ScanSearch, Library,
} from "lucide-react";

export type Bi = { en: string; hi: string };
export type NavItem = { href: string; label: Bi; desc: Bi; icon: any; match?: string[] };
export type NavGroup = { id: string; label: Bi; icon: any; items: NavItem[]; href?: string };

export const NAV_GROUPS: NavGroup[] = [
  {
    id: "standards",
    label: { en: "Find Standards", hi: "मानक खोजें" },
    icon: Search,
    items: [
      { href: "/recommend", icon: Search, match: ["/recommend", "/analysis"],
        label: { en: "Find the right standard", hi: "सही मानक खोजें" },
        desc: { en: "Describe a product in plain words — get the Indian Standard, its editions and mandatory certification.", hi: "उत्पाद का सरल वर्णन करें — भारतीय मानक, संस्करण और अनिवार्य प्रमाणन पाएँ।" } },
      { href: "/search", icon: Library, match: ["/search", "/standards"],
        label: { en: "Browse the standards catalogue", hi: "मानक सूची देखें" },
        desc: { en: "Look up any IS number and see its status, amendments and related standards.", hi: "कोई भी IS संख्या खोजें — स्थिति, संशोधन और संबंधित मानक देखें।" } },
      { href: "/kg", icon: Network, match: ["/kg"],
        label: { en: "Knowledge graph", hi: "ज्ञान ग्राफ़" },
        desc: { en: "See how items, standards, regulations, tests and labs connect to each other.", hi: "देखें कि वस्तुएँ, मानक, नियम, परीक्षण और प्रयोगशालाएँ कैसे जुड़े हैं।" } },
      { href: "/tools", icon: Wrench, match: ["/tools"],
        label: { en: "Standards tools", hi: "मानक उपकरण" },
        desc: { en: "Compare equivalent standards, check a standard on a past date, browse the rule list.", hi: "समकक्ष मानकों की तुलना, पुरानी तिथि पर मानक जाँच, नियम सूची।" } },
    ],
  },
  {
    id: "officer",
    label: { en: "For Officers", hi: "अधिकारियों हेतु" },
    icon: UserCog,
    items: [
      { href: "/officer", icon: UserCog, match: ["/officer"],
        label: { en: "Officer workspace", hi: "अधिकारी कार्यक्षेत्र" },
        desc: { en: "Your tenders, what needs attention today, and regulatory alerts.", hi: "आपकी निविदाएँ, आज के लंबित कार्य और नियामक सूचनाएँ।" } },
      { href: "/studio", icon: FilePlus2, match: ["/studio"],
        label: { en: "Create a new tender", hi: "नई निविदा बनाएँ" },
        desc: { en: "Write one sentence about what you need — get a complete, checked draft tender.", hi: "एक वाक्य में आवश्यकता लिखें — पूर्ण, जाँचा हुआ निविदा प्रारूप पाएँ।" } },
      { href: "/tenders", icon: FileSearch, match: ["/tenders"],
        label: { en: "Check an existing tender", hi: "मौजूदा निविदा जाँचें" },
        desc: { en: "Upload a tender document to find errors, outdated standards and unfair clauses before publishing.", hi: "प्रकाशन से पहले त्रुटियाँ, पुराने मानक और अनुचित खंड खोजने हेतु निविदा अपलोड करें।" } },
      { href: "/radar", icon: Radar, match: ["/radar"],
        label: { en: "Regulatory radar", hi: "नियामक रडार" },
        desc: { en: "When a standard or Quality Control Order changes, see which tenders are affected.", hi: "मानक या गुणवत्ता नियंत्रण आदेश बदलने पर प्रभावित निविदाएँ देखें।" } },
    ],
  },
  {
    id: "contractor",
    label: { en: "For Bidders", hi: "बोलीदाताओं हेतु" },
    icon: Briefcase,
    items: [
      { href: "/contractor", icon: Briefcase, match: ["/contractor"],
        label: { en: "Bidder workspace", hi: "बोलीदाता कार्यक्षेत्र" },
        desc: { en: "Tenders open to you, bids you have submitted and their results.", hi: "आपके लिए खुली निविदाएँ, जमा बोलियाँ और परिणाम।" } },
      { href: "/market", icon: Store, match: ["/market"],
        label: { en: "Open tenders", hi: "खुली निविदाएँ" },
        desc: { en: "Browse tenders accepting bids and fill a bid form that checks itself.", hi: "बोली हेतु खुली निविदाएँ देखें और स्वयं-जाँच वाला बोली फ़ॉर्म भरें।" } },
      { href: "/bidder", icon: ScanSearch, match: ["/bidder", "/bids", "/passport"],
        label: { en: "Check my documents (Bid Mirror)", hi: "मेरे दस्तावेज़ जाँचें (बोली दर्पण)" },
        desc: { en: "Upload datasheets, licences and test reports — see which tender requirements they prove.", hi: "डेटाशीट, लाइसेंस, परीक्षण रिपोर्ट अपलोड करें — कौन-सी आवश्यकताएँ सिद्ध होती हैं देखें।" } },
      { href: "/extension", icon: Puzzle, match: ["/extension"],
        label: { en: "Browser extension", hi: "ब्राउज़र एक्सटेंशन" },
        desc: { en: "Standards help right inside GeM and CPPP tender pages.", hi: "GeM और CPPP निविदा पृष्ठों पर ही मानक सहायता।" } },
    ],
  },
  {
    id: "audit",
    label: { en: "Audit Ledger", hi: "लेखा परीक्षा बही" },
    icon: Link2,
    href: "/ledger",
    items: [
      { href: "/ledger", icon: Link2, match: ["/ledger"],
        label: { en: "Audit ledger", hi: "लेखा परीक्षा बही" },
        desc: { en: "Every decision, recorded in a tamper-evident log anyone can verify.", hi: "हर निर्णय — छेड़छाड़-रोधी लॉग में दर्ज, कोई भी सत्यापित कर सकता है।" } },
    ],
  },
  {
    id: "about",
    label: { en: "About", hi: "परिचय" },
    icon: Info,
    items: [
      { href: "/about", icon: Info, match: ["/about"],
        label: { en: "About SpecSure", hi: "स्पेकश्योर परिचय" },
        desc: { en: "The problem we solve and how the system works.", hi: "हम कौन-सी समस्या हल करते हैं और प्रणाली कैसे काम करती है।" } },
      { href: "/evidence", icon: Gauge, match: ["/evidence"],
        label: { en: "How well it works", hi: "यह कितना सटीक है" },
        desc: { en: "Measured accuracy on real tenders and standards — with the method.", hi: "वास्तविक निविदाओं और मानकों पर मापी गई सटीकता — विधि सहित।" } },
      { href: "/about#disclaimer", icon: BookOpen,
        label: { en: "Disclaimer & data sources", hi: "अस्वीकरण व डेटा स्रोत" },
        desc: { en: "Where the data comes from and what this prototype does not do.", hi: "डेटा कहाँ से आता है और यह प्रोटोटाइप क्या नहीं करता।" } },
    ],
  },
];

/** Friendly names for the second part of a URL (e.g. /tenders/<id>) so breadcrumbs never show a raw id alone. */
export const DETAIL_LABEL: Record<string, Bi> = {
  tenders: { en: "Tender file", hi: "निविदा फ़ाइल" },
  market: { en: "Bid form", hi: "बोली फ़ॉर्म" },
  bids: { en: "Bid Mirror result", hi: "बोली दर्पण परिणाम" },
  passport: { en: "Compliance passport", hi: "अनुपालन पासपोर्ट" },
  standards: { en: "Standard", hi: "मानक" },
  analysis: { en: "Analysis result", hi: "विश्लेषण परिणाम" },
};

/** Where each top-level page sits in the site map — used for breadcrumbs. */
export function locate(pathname: string): { group?: NavGroup; item?: NavItem } {
  for (const g of NAV_GROUPS) {
    for (const it of g.items) {
      const m = it.match || [it.href];
      if (m.some((x) => pathname === x || pathname.startsWith(x + "/"))) return { group: g, item: it };
    }
  }
  return {};
}

