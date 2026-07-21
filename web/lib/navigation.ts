import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BarChart3,
  Boxes,
  Brain,
  Briefcase,
  Building2,
  Eye,
  FileSearch,
  FileText,
  FlaskConical,
  Info,
  LayoutDashboard,
  LifeBuoy,
  LineChart,
  MessageSquare,
  Network,
  Settings,
  ShieldCheck,
  Sparkles,
  Target,
} from "lucide-react";
import type { Role } from "@/types/api";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  roles?: Role[]; // if set, only these roles see it
}

export interface NavSection {
  title: string;
  items: NavItem[];
}

export const NAV_SECTIONS: NavSection[] = [
  {
    title: "Decisioning",
    items: [
      { href: "/", label: "Dashboard", icon: LayoutDashboard },
      { href: "/decisions", label: "Decision Center", icon: Target },
      { href: "/companies", label: "Companies", icon: Building2 },
      { href: "/watchlist", label: "Watchlist", icon: Eye },
      { href: "/portfolio", label: "Portfolio", icon: Briefcase },
    ],
  },
  {
    title: "Intelligence",
    items: [
      { href: "/research", label: "Research", icon: Sparkles },
      { href: "/evidence", label: "Evidence Center", icon: FileSearch },
      { href: "/knowledge-graph", label: "Knowledge Graph", icon: Network },
      { href: "/feature-store", label: "Feature Store", icon: Boxes },
      { href: "/probability", label: "Probability", icon: Brain },
    ],
  },
  {
    title: "Analysis",
    items: [
      { href: "/backtest", label: "Backtest", icon: LineChart },
      { href: "/scenario", label: "Scenario Simulator", icon: FlaskConical },
      { href: "/market", label: "Market", icon: BarChart3 },
      { href: "/universe", label: "Universe", icon: Boxes, roles: ["ANALYST", "ADMIN"] },
      { href: "/reports", label: "Reports", icon: FileText },
    ],
  },
  {
    title: "System",
    items: [
      { href: "/admin", label: "Administration", icon: ShieldCheck, roles: ["ADMIN"] },
      { href: "/settings", label: "Settings", icon: Settings },
      { href: "/profile", label: "Profile", icon: Activity },
    ],
  },
  {
    title: "Support",
    items: [
      { href: "/help", label: "Help Center", icon: LifeBuoy },
      { href: "/feedback", label: "Feedback", icon: MessageSquare },
      { href: "/about", label: "About", icon: Info },
    ],
  },
];
