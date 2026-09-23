/** Deterministic seed data generator for Bazaar Multi-Vendor Commerce Platform. */

import { randomUUID } from "node:crypto";

function esc(val) {
  if (val === null || val === undefined) return "NULL";
  if (typeof val === "boolean") return val ? "TRUE" : "FALSE";
  if (typeof val === "number") return String(val);
  return `'${String(val).replace(/'/g, "''")}'`;
}

function escJson(obj) {
  if (!obj) return "'{}'::jsonb";
  return `'${JSON.stringify(obj).replace(/'/g, "''")}'::jsonb`;
}

function escArray(arr) {
  if (!arr || arr.length === 0) return "'{}'";
  return `ARRAY[${arr.map(esc).join(", ")}]::text[]`;
}

const HASH_SHOPPER =
  "e49299f2f9d87845cebfa27412d5be4d:8debb361bfc0c483e6363829fd8b6aa852f011b97ed4b8a22ced4f7a8acb43dba1cf950499fad2cf3f80001e52cb23d615ce1d45493ca257dce24ba9370a8eee";
const HASH_VENDOR =
  "57d72a9838f99e8261787ab3cb0c829e:12a9eac5434fe281d9aaa5f60b8daf8fc15db7a902c8cfd9154e23e5b7e0ac5501e0a792160a0b5a3f67f1bc4b95b1c8a584d5c0e49e4dc57eb0631ed58ff01f";
const HASH_ADMIN =
  "52380a8eb79d12fe872c880dbf9aa0c2:f34715bdf233c7b32881ed33183aed71f62c511513a1ce4af7be4194e526cba619b3df205ba161d1bf1813286640e742cb32f1028103bcb65dfbc2b0462f72bd";
const HASH_COMMON =
  "c570b662aa7dbc4dccc8c9956b409e0e:f6397d3425e9b341d76b396cfc1af12d3849727d90bfb11554ec4a41a4d3c6280e98df13ad89b29040800dc8cbca73100f3702845235afd69546a5884b828f32";

const lines = [];
function out(str) {
  lines.push(str);
}

out(`-- ====================================================================`);
out(`-- Bazaar Multi-Vendor Commerce Platform: Deterministic Demo Seed Data`);
out(`-- ====================================================================`);
out(``);

// 1. Categories
const CATEGORIES = [
  {
    id: "10000000-0000-0000-0000-000000000001",
    slug: "apparel-ethnic",
    name: "Ethnic Wear & Handloom",
    description: "Handcrafted sarees, kurtas, bandhgalas, and heritage weaves from across India.",
    imageUrl: "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=600&auto=format&fit=crop",
    sortOrder: 1,
  },
  {
    id: "10000000-0000-0000-0000-000000000002",
    slug: "home-decor",
    name: "Artisanal Home & Decor",
    description: "Terracotta pottery, brass idols, dhurrie rugs, and hand-carved wood art.",
    imageUrl: "https://images.unsplash.com/photo-1616046229478-9901c5536a45?w=600&auto=format&fit=crop",
    sortOrder: 2,
  },
  {
    id: "10000000-0000-0000-0000-000000000003",
    slug: "gourmet-spices",
    name: "Gourmet Foods & Spices",
    description: "Single-origin hill teas, GI-tagged Malabar spices, cold-pressed oils, and forest honey.",
    imageUrl: "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=600&auto=format&fit=crop",
    sortOrder: 3,
  },
  {
    id: "10000000-0000-0000-0000-000000000004",
    slug: "jewelry-crafts",
    name: "Handmade Fine Jewelry",
    description: "Silver filigree, temple jewelry, Kundan meenakari, and certified baroque pearls.",
    imageUrl: "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=600&auto=format&fit=crop",
    sortOrder: 4,
  },
  {
    id: "10000000-0000-0000-0000-000000000005",
    slug: "ayurveda-wellness",
    name: "Ayurveda & Herbal Care",
    description: "Pure Kumkumadi oils, wild-harvested herbs, natural soaps, and aromatherapy diffusers.",
    imageUrl: "https://images.unsplash.com/photo-1608248597358-1f19659e51b3?w=600&auto=format&fit=crop",
    sortOrder: 5,
  },
  {
    id: "10000000-0000-0000-0000-000000000006",
    slug: "leather-footwear",
    name: "Crafted Footwear & Leather",
    description: "Hand-embroidered Rajasthani juttis, Kolhapuri chappals, and veg-tan leather journals.",
    imageUrl: "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=600&auto=format&fit=crop",
    sortOrder: 6,
  },
];

out(`-- 1. Categories`);
for (const cat of CATEGORIES) {
  out(
    `INSERT INTO categories (id, slug, name, description, image_url, sort_order) VALUES (${esc(
      cat.id
    )}, ${esc(cat.slug)}, ${esc(cat.name)}, ${esc(cat.description)}, ${esc(cat.imageUrl)}, ${cat.sortOrder}) ON CONFLICT (slug) DO NOTHING;`
  );
}
out(``);

// 2. Demo Users
const USER_SHOPPER = {
  id: "20000000-0000-0000-0000-000000000001",
  email: "priya@bazaar.test",
  name: "Priya Sharma",
  role: "shopper",
  phone: "+91 98765 43210",
  avatarUrl: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop",
};

const USER_VENDOR = {
  id: "20000000-0000-0000-0000-000000000002",
  email: "aryan@bazaar.test",
  name: "Aryan Gupta",
  role: "vendor",
  phone: "+91 98111 22334",
  avatarUrl: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&auto=format&fit=crop",
};

const USER_ADMIN = {
  id: "20000000-0000-0000-0000-000000000003",
  email: "admin@bazaar.test",
  name: "Vikram Mehta",
  role: "admin",
  phone: "+91 99999 88888",
  avatarUrl: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&auto=format&fit=crop",
};

out(`-- 2. Core Demo Users`);
out(
  `INSERT INTO users (id, email, password_hash, role, name, phone, avatar_url) VALUES
  (${esc(USER_SHOPPER.id)}, ${esc(USER_SHOPPER.email)}, ${esc(HASH_SHOPPER)}, 'shopper', ${esc(USER_SHOPPER.name)}, ${esc(USER_SHOPPER.phone)}, ${esc(USER_SHOPPER.avatarUrl)}),
  (${esc(USER_VENDOR.id)}, ${esc(USER_VENDOR.email)}, ${esc(HASH_VENDOR)}, 'vendor', ${esc(USER_VENDOR.name)}, ${esc(USER_VENDOR.phone)}, ${esc(USER_VENDOR.avatarUrl)}),
  (${esc(USER_ADMIN.id)}, ${esc(USER_ADMIN.email)}, ${esc(HASH_ADMIN)}, 'admin', ${esc(USER_ADMIN.name)}, ${esc(USER_ADMIN.phone)}, ${esc(USER_ADMIN.avatarUrl)})
  ON CONFLICT (email) DO NOTHING;`
);
out(``);

// 3. Shopper Address
out(`-- 3. Shopper Default Addresses`);
out(
  `INSERT INTO user_addresses (user_id, label, recipient_name, phone, street, city, state, postal_code, country, is_default) VALUES
  (${esc(USER_SHOPPER.id)}, 'home', 'Priya Sharma', '+91 98765 43210', 'Flat 402, Lotus Greens, Indiranagar', 'Bengaluru', 'Karnataka', '560038', 'India', TRUE),
  (${esc(USER_SHOPPER.id)}, 'office', 'Priya Sharma (Work)', '+91 98765 43210', 'WeWork Galaxy, 43 Residency Rd, Shanthala Nagar', 'Bengaluru', 'Karnataka', '560025', 'India', FALSE);`
);
out(``);

// 4. Vendors & Shops
const SHOPS = [
  {
    id: "30000000-0000-0000-0000-000000000001",
    userId: USER_VENDOR.id,
    slug: "craftloom",
    name: "Craftloom Studio",
    tagline: "Hand-spun Chanderi & Mulmul weaves from central India",
    description: "Craftloom Studio partners directly with over 120 master weavers in Madhya Pradesh to craft timeless Chanderi sarees, stoles, and block-printed tunic fabrics.",
    logoUrl: "https://images.unsplash.com/photo-1544816155-12df9643f363?w=200&auto=format&fit=crop",
    bannerUrl: "https://images.unsplash.com/photo-1558769132-cb1aea458c5e?w=1200&auto=format&fit=crop",
    kycStatus: "verified",
    commissionRate: 1000,
    bankName: "HDFC Bank",
    bankLast4: "4921",
    bankIfsc: "HDFC0001234",
    ratingAvg: 4.92,
    ratingCount: 148,
  },
  {
    id: "30000000-0000-0000-0000-000000000002",
    userId: "20000000-0000-0000-0000-000000000010",
    ownerName: "Sunita Reddy",
    ownerEmail: "sunita@rangolisilks.test",
    slug: "rangoli-silks",
    name: "Rangoli Silks",
    tagline: "Pure Kanjeevaram & Banarasi heirloom silk sarees",
    description: "Authentic silk mark certified sarees woven with real zari borders by traditional weaving clusters in Kanchipuram and Varanasi.",
    logoUrl: "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=200&auto=format&fit=crop",
    bannerUrl: "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=1200&auto=format&fit=crop",
    kycStatus: "verified",
    commissionRate: 800,
    bankName: "State Bank of India",
    bankLast4: "8812",
    bankIfsc: "SBIN0004567",
    ratingAvg: 4.88,
    ratingCount: 92,
  },
  {
    id: "30000000-0000-0000-0000-000000000003",
    userId: "20000000-0000-0000-0000-000000000011",
    ownerName: "Devendra Joshi",
    ownerEmail: "devendra@mittiearth.test",
    slug: "mitti-earth",
    name: "Mitti Earth Studio",
    tagline: "Studio pottery, terracotta serveware & ceramic dining",
    description: "Handcrafted stoneware, glazed terracotta bowls, and rustic tea sets fired at 1200°C for modern dining spaces.",
    logoUrl: "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?w=200&auto=format&fit=crop",
    bannerUrl: "https://images.unsplash.com/photo-1616046229478-9901c5536a45?w=1200&auto=format&fit=crop",
    kycStatus: "verified",
    commissionRate: 1000,
    bankName: "ICICI Bank",
    bankLast4: "3104",
    bankIfsc: "ICIC0000890",
    ratingAvg: 4.95,
    ratingCount: 215,
  },
  {
    id: "30000000-0000-0000-0000-000000000004",
    userId: "20000000-0000-0000-0000-000000000012",
    ownerName: "Farhan Qureshi",
    ownerEmail: "farhan@brassbloom.test",
    slug: "brass-bloom",
    name: "Brass & Bloom",
    tagline: "Moradabad hand-cast brass planters, lamps & urli bowls",
    description: "Artisan brassware celebrating antique patinas, floral engravings, and ambient festive diya lighting.",
    logoUrl: "https://images.unsplash.com/photo-1544816155-12df9643f363?w=200&auto=format&fit=crop",
    bannerUrl: "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=1200&auto=format&fit=crop",
    kycStatus: "verified",
    commissionRate: 1200,
    bankName: "Axis Bank",
    bankLast4: "7019",
    bankIfsc: "UTIB0001122",
    ratingAvg: 4.79,
    ratingCount: 76,
  },
  {
    id: "30000000-0000-0000-0000-000000000005",
    userId: "20000000-0000-0000-0000-000000000013",
    ownerName: "George Mathew",
    ownerEmail: "george@spiceroute.test",
    slug: "spice-route",
    name: "Spice Route Organics",
    tagline: "Single-estate Wayanad black pepper, green cardamom & turmeric",
    description: "Harvested from rainforest shade canopy estates in Kerala. Certified organic, hand-sorted, and vacuum packed for culinary perfection.",
    logoUrl: "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=200&auto=format&fit=crop",
    bannerUrl: "https://images.unsplash.com/photo-1509358271058-acd22cc93898?w=1200&auto=format&fit=crop",
    kycStatus: "verified",
    commissionRate: 1000,
    bankName: "Federal Bank",
    bankLast4: "1590",
    bankIfsc: "FDRL0001923",
    ratingAvg: 4.96,
    ratingCount: 340,
  },
  {
    id: "30000000-0000-0000-0000-000000000006",
    userId: "20000000-0000-0000-0000-000000000014",
    ownerName: "Meera Agarwal",
    ownerEmail: "meera@silvermoon.test",
    slug: "silver-moon",
    name: "Silver Moon Jewels",
    tagline: "92.5 Hallmarked sterling silver filigree & tribal neckpieces",
    description: "Fine silver jewelry handcrafted by master artisans in Cuttack and Jaipur, featuring natural semi-precious gemstones.",
    logoUrl: "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=200&auto=format&fit=crop",
    bannerUrl: "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=1200&auto=format&fit=crop",
    kycStatus: "verified",
    commissionRate: 1500,
    bankName: "Kotak Mahindra Bank",
    bankLast4: "6643",
    bankIfsc: "KKBK0000214",
    ratingAvg: 4.91,
    ratingCount: 118,
  },
  {
    id: "30000000-0000-0000-0000-000000000007",
    userId: "20000000-0000-0000-0000-000000000015",
    ownerName: "Dr. Ananya Vaidya",
    ownerEmail: "ananya@vedicroots.test",
    slug: "vedic-roots",
    name: "Vedic Roots Botanicals",
    tagline: "Small-batch Ayurvedic skincare & cold-pressed therapeutic oils",
    description: "Prepared according to Ashtanga Hridaya formulations using organic herbs, cow's milk, and cold-pressed sesame oil in brass cauldrons.",
    logoUrl: "https://images.unsplash.com/photo-1608248597358-1f19659e51b3?w=200&auto=format&fit=crop",
    bannerUrl: "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=1200&auto=format&fit=crop",
    kycStatus: "verified",
    commissionRate: 1000,
    bankName: "HDFC Bank",
    bankLast4: "9021",
    bankIfsc: "HDFC0000561",
    ratingAvg: 4.87,
    ratingCount: 88,
  },
  {
    id: "30000000-0000-0000-0000-000000000008",
    userId: "20000000-0000-0000-0000-000000000016",
    ownerName: "Manish Rathore",
    ownerEmail: "manish@royalmojari.test",
    slug: "royal-mojari",
    name: "Royal Mojari Co.",
    tagline: "Hand-stitched leather juttis with zardozi & dabka embroidery",
    description: "Cushioned genuine leather soles hand-stitched by multigenerational jutti artisans in Jodhpur for weddings and festivities.",
    logoUrl: "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=200&auto=format&fit=crop",
    bannerUrl: "https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=1200&auto=format&fit=crop",
    kycStatus: "verified",
    commissionRate: 1000,
    bankName: "Bank of Baroda",
    bankLast4: "5512",
    bankIfsc: "BARB0JODHPU",
    ratingAvg: 4.82,
    ratingCount: 64,
  },
];

out(`-- 4. Vendor Owners and Shops`);
for (const shop of SHOPS) {
  if (shop.ownerEmail) {
    out(
      `INSERT INTO users (id, email, password_hash, role, name, is_active) VALUES (${esc(
        shop.userId
      )}, ${esc(shop.ownerEmail)}, ${esc(HASH_COMMON)}, 'vendor', ${esc(
        shop.ownerName
      )}, TRUE) ON CONFLICT (email) DO NOTHING;`
    );
  }
  out(
    `INSERT INTO shops (id, user_id, slug, name, tagline, description, logo_url, banner_url, kyc_status, commission_rate_basis_points, bank_name, bank_account_last4, bank_ifsc_code, rating_avg, rating_count) VALUES (${esc(
      shop.id
    )}, ${esc(shop.userId)}, ${esc(shop.slug)}, ${esc(shop.name)}, ${esc(
      shop.tagline
    )}, ${esc(shop.description)}, ${esc(shop.logoUrl)}, ${esc(shop.bannerUrl)}, ${esc(
      shop.kycStatus
    )}, ${shop.commissionRate}, ${esc(shop.bankName)}, ${esc(shop.bankLast4)}, ${esc(
      shop.bankIfsc
    )}, ${shop.ratingAvg}, ${shop.ratingCount}) ON CONFLICT (slug) DO NOTHING;`
  );
}
out(``);

// 5. Products & Variants Catalog
const PRODUCTS = [
  // Shop 1: Craftloom Studio (Aryan Gupta)
  {
    id: "40000000-0000-0000-0000-000000000001",
    shopId: SHOPS[0].id,
    categoryId: CATEGORIES[0].id,
    title: "Chanderi Handloom Silk Saree with Zari Booti",
    slug: "chanderi-silk-saree-zari-booti",
    description: "Featherlight handloom Chanderi saree crafted with pure mulberry silk warp and high-twist cotton weft. Embellished with hand-woven golden zari floral bootis and an ornate pallu border.",
    tags: ["chanderi", "handloom", "saree", "silk", "ethnic", "wedding"],
    basePriceCents: 499900,
    comparePriceCents: 650000,
    isFeatured: true,
    ratingAvg: 4.95,
    ratingCount: 42,
    variants: [
      {
        sku: "CL-CHN-SRE-GLD",
        title: "Sunset Amber & Gold Zari",
        optionColor: "Sunset Amber",
        optionSize: "Free Size (6.3m)",
        priceCents: 499900,
        comparePriceCents: 650000,
        stock: 35,
        imageUrl: "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=600&auto=format&fit=crop",
      },
      {
        sku: "CL-CHN-SRE-EMR",
        title: "Emerald Green & Antique Zari",
        optionColor: "Emerald Green",
        optionSize: "Free Size (6.3m)",
        priceCents: 529900,
        comparePriceCents: 690000,
        stock: 22,
        imageUrl: "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=600&auto=format&fit=crop",
      },
      {
        sku: "CL-CHN-SRE-RBY",
        title: "Ruby Wine & Silver Zari",
        optionColor: "Ruby Wine",
        optionSize: "Free Size (6.3m)",
        priceCents: 529900,
        comparePriceCents: 690000,
        stock: 18,
        imageUrl: "https://images.unsplash.com/photo-1617627143750-d86bc21e42bb?w=600&auto=format&fit=crop",
      },
    ],
  },
  {
    id: "40000000-0000-0000-0000-000000000002",
    shopId: SHOPS[0].id,
    categoryId: CATEGORIES[0].id,
    title: "Bagru Hand Block Printed Mulmul Kurta Set",
    slug: "bagru-block-print-mulmul-kurta",
    description: "Breathable 100% mulmul cotton straight kurta accompanied by tapered pants and a sheer chiffon dupatta. Printed using natural indigo and madder dyes in Bagru, Rajasthan.",
    tags: ["mulmul", "kurta-set", "block-print", "natural-dye", "cotton"],
    basePriceCents: 249900,
    comparePriceCents: 320000,
    isFeatured: true,
    ratingAvg: 4.88,
    ratingCount: 56,
    variants: [
      {
        sku: "CL-BGR-KRT-IND-S",
        title: "Indigo Blue / Size S",
        optionColor: "Indigo Blue",
        optionSize: "S (36)",
        priceCents: 249900,
        stock: 25,
        imageUrl: "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=600&auto=format&fit=crop",
      },
      {
        sku: "CL-BGR-KRT-IND-M",
        title: "Indigo Blue / Size M",
        optionColor: "Indigo Blue",
        optionSize: "M (38)",
        priceCents: 249900,
        stock: 40,
        imageUrl: "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=600&auto=format&fit=crop",
      },
      {
        sku: "CL-BGR-KRT-IND-L",
        title: "Indigo Blue / Size L",
        optionColor: "Indigo Blue",
        optionSize: "L (40)",
        priceCents: 249900,
        stock: 30,
        imageUrl: "https://images.unsplash.com/photo-1583391733956-3750e0ff4e8b?w=600&auto=format&fit=crop",
      },
    ],
  },
  // Shop 2: Rangoli Silks
  {
    id: "40000000-0000-0000-0000-000000000003",
    shopId: SHOPS[1].id,
    categoryId: CATEGORIES[0].id,
    title: "Kanjivaram Pure Bridal Silk Saree with Temple Border",
    slug: "kanjivaram-pure-bridal-silk-saree",
    description: "Heirloom bridal Kanjivaram woven with 3-ply heavy mulberry silk and certified gold-plated silver zari. Features traditional korvai temple borders and peacock motifs.",
    tags: ["kanjivaram", "silk-mark", "bridal", "saree", "heritage"],
    basePriceCents: 1899900,
    comparePriceCents: 2400000,
    isFeatured: true,
    ratingAvg: 4.98,
    ratingCount: 31,
    variants: [
      {
        sku: "RS-KNJ-BRD-CRMS",
        title: "Crimson Red & Mustard Korvai",
        optionColor: "Crimson Red",
        optionSize: "Free Size (6.3m)",
        priceCents: 1899900,
        stock: 12,
        imageUrl: "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=600&auto=format&fit=crop",
      },
      {
        sku: "RS-KNJ-BRD-ROYAL",
        title: "Royal Peacock Blue & Gold",
        optionColor: "Royal Blue",
        optionSize: "Free Size (6.3m)",
        priceCents: 1999900,
        stock: 8,
        imageUrl: "https://images.unsplash.com/photo-1617627143750-d86bc21e42bb?w=600&auto=format&fit=crop",
      },
    ],
  },
  // Shop 3: Mitti Earth Studio
  {
    id: "40000000-0000-0000-0000-000000000004",
    shopId: SHOPS[2].id,
    categoryId: CATEGORIES[1].id,
    title: "Speckled Stoneware Dinner Set (18 Pieces)",
    slug: "speckled-stoneware-dinner-set",
    description: "Complete handcrafted dining collection for 6 persons. Includes 6 dinner plates, 6 side plates, and 6 soup bowls with artisan matte glaze and raw clay foot rim.",
    tags: ["stoneware", "ceramics", "dinner-set", "pottery", "dining"],
    basePriceCents: 649900,
    comparePriceCents: 850000,
    isFeatured: true,
    ratingAvg: 4.97,
    ratingCount: 78,
    variants: [
      {
        sku: "ME-DIN-SET-OAT",
        title: "Oatmeal Speckle (Matte)",
        optionColor: "Oatmeal Speckle",
        optionSize: "18-Piece Set",
        priceCents: 649900,
        stock: 20,
        imageUrl: "https://images.unsplash.com/photo-1616046229478-9901c5536a45?w=600&auto=format&fit=crop",
      },
      {
        sku: "ME-DIN-SET-SGE",
        title: "Sage Green & Sand",
        optionColor: "Sage Green",
        optionSize: "18-Piece Set",
        priceCents: 699900,
        stock: 15,
        imageUrl: "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?w=600&auto=format&fit=crop",
      },
    ],
  },
  {
    id: "40000000-0000-0000-0000-000000000005",
    shopId: SHOPS[2].id,
    categoryId: CATEGORIES[1].id,
    title: "Hand-thrown Terracotta Chai Kulhad Set (Pack of 6)",
    slug: "terracotta-chai-kulhad-pack-of-6",
    description: "Traditional porous terracotta cups cured with natural mustard oil. Imparts an authentic earthy aroma (saundhi mitti) to your morning masala chai.",
    tags: ["chai", "kulhad", "terracotta", "handmade", "tea"],
    basePriceCents: 79900,
    comparePriceCents: 120000,
    isFeatured: false,
    ratingAvg: 4.92,
    ratingCount: 134,
    variants: [
      {
        sku: "ME-KUL-6PK-RAW",
        title: "Raw Natural Clay (180ml)",
        optionColor: "Natural Terracotta",
        optionSize: "6-Pack",
        priceCents: 79900,
        stock: 150,
        imageUrl: "https://images.unsplash.com/photo-1578749556568-bc2c40e68b61?w=600&auto=format&fit=crop",
      },
    ],
  },
  // Shop 4: Brass & Bloom
  {
    id: "40000000-0000-0000-0000-000000000006",
    shopId: SHOPS[3].id,
    categoryId: CATEGORIES[1].id,
    title: "Antique Engraved Brass Urli Bowl with Floral Handles",
    slug: "antique-engraved-brass-urli-bowl",
    description: "Solid heavy-gauge brass urli bowl for floating flowers and tea light candles. Hand-chiseled with traditional peacock and lotus motifs by Moradabad artisans.",
    tags: ["brass", "urli", "home-decor", "festive", "diya"],
    basePriceCents: 349900,
    comparePriceCents: 450000,
    isFeatured: true,
    ratingAvg: 4.85,
    ratingCount: 47,
    variants: [
      {
        sku: "BB-URL-12IN-GLD",
        title: "12-Inch Antique Brass Finish",
        optionColor: "Antique Gold",
        optionSize: "12-Inch Diameter",
        priceCents: 349900,
        stock: 28,
        imageUrl: "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=600&auto=format&fit=crop",
      },
      {
        sku: "BB-URL-16IN-GLD",
        title: "16-Inch Grand Statement Bowl",
        optionColor: "Antique Gold",
        optionSize: "16-Inch Diameter",
        priceCents: 499900,
        stock: 14,
        imageUrl: "https://images.unsplash.com/photo-1544816155-12df9643f363?w=600&auto=format&fit=crop",
      },
    ],
  },
  // Shop 5: Spice Route Organics
  {
    id: "40000000-0000-0000-0000-000000000007",
    shopId: SHOPS[4].id,
    categoryId: CATEGORIES[2].id,
    title: "Wayanad Bold Black Tellicherry Peppercorns (500g)",
    slug: "wayanad-tellicherry-peppercorns-500g",
    description: "Grade TGSEB (Tellicherry Garbled Special Extra Bold) whole black peppercorns. Matured on the vine for maximum piperine content, complex fruity aromas, and intense heat.",
    tags: ["black-pepper", "organic", "spices", "tellicherry", "gourmet"],
    basePriceCents: 99900,
    comparePriceCents: 140000,
    isFeatured: true,
    ratingAvg: 4.99,
    ratingCount: 182,
    variants: [
      {
        sku: "SR-PEP-500G-VAC",
        title: "500g Resealable Aroma Pouch",
        optionColor: "Whole Black",
        optionSize: "500g",
        priceCents: 99900,
        stock: 85,
        imageUrl: "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=600&auto=format&fit=crop",
      },
      {
        sku: "SR-PEP-1KG-VAC",
        title: "1kg Pantry Bulk Pack",
        optionColor: "Whole Black",
        optionSize: "1000g (1kg)",
        priceCents: 184900,
        stock: 45,
        imageUrl: "https://images.unsplash.com/photo-1509358271058-acd22cc93898?w=600&auto=format&fit=crop",
      },
    ],
  },
  {
    id: "40000000-0000-0000-0000-000000000008",
    shopId: SHOPS[4].id,
    categoryId: CATEGORIES[2].id,
    title: "Kashmiri Mongra Saffron Grade-A (2 Grams)",
    slug: "kashmiri-mongra-saffron-grade-a",
    description: "Certified GI Pampore saffron threads with thick crimson tips and zero yellow floral styles. Laboratory tested with high crocin color strength above 240.",
    tags: ["saffron", "kesar", "kashmir", "mongra", "gourmet"],
    basePriceCents: 129900,
    comparePriceCents: 175000,
    isFeatured: true,
    ratingAvg: 4.95,
    ratingCount: 96,
    variants: [
      {
        sku: "SR-SAF-2G-BOX",
        title: "2g Sealed Wooden Gift Box",
        optionColor: "Deep Crimson",
        optionSize: "2 Grams",
        priceCents: 129900,
        stock: 60,
        imageUrl: "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=600&auto=format&fit=crop",
      },
    ],
  },
  // Shop 6: Silver Moon Jewels
  {
    id: "40000000-0000-0000-0000-000000000009",
    shopId: SHOPS[5].id,
    categoryId: CATEGORIES[3].id,
    title: "925 Sterling Silver Chandbali Earrings with Pearls",
    slug: "925-silver-chandbali-earrings-pearls",
    description: "Classic crescent moon silhouette crafted with 92.5 sterling silver in antique oxidized patina, accented with freshwater seed pearls and push-back clasps.",
    tags: ["silver", "chandbali", "earrings", "925", "jewelry", "pearls"],
    basePriceCents: 389900,
    comparePriceCents: 520000,
    isFeatured: true,
    ratingAvg: 4.93,
    ratingCount: 52,
    variants: [
      {
        sku: "SM-CHD-925-OXI",
        title: "Oxidized Silver with Seed Pearls",
        optionColor: "Oxidized Silver",
        optionSize: "Length: 5.5cm",
        priceCents: 389900,
        stock: 30,
        imageUrl: "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=600&auto=format&fit=crop",
      },
    ],
  },
  // Shop 7: Vedic Roots Botanicals
  {
    id: "40000000-0000-0000-0000-000000000010",
    shopId: SHOPS[6].id,
    categoryId: CATEGORIES[4].id,
    title: "Kumkumadi Miraculous Night Radiance Facial Oil (30ml)",
    slug: "kumkumadi-night-radiance-oil-30ml",
    description: "Authentic classical formulation containing 26 Himalayan herbs infused in sesame oil and saffron. Helps brighten dull skin, even pigmentation, and reduce fine lines.",
    tags: ["kumkumadi", "face-oil", "ayurveda", "saffron", "organic-skincare"],
    basePriceCents: 189900,
    comparePriceCents: 249900,
    isFeatured: true,
    ratingAvg: 4.89,
    ratingCount: 65,
    variants: [
      {
        sku: "VR-KUM-30ML-DRP",
        title: "30ml Dropper Glass Bottle",
        optionColor: "Golden Oil",
        optionSize: "30ml",
        priceCents: 189900,
        stock: 75,
        imageUrl: "https://images.unsplash.com/photo-1608248597358-1f19659e51b3?w=600&auto=format&fit=crop",
      },
    ],
  },
  // Shop 8: Royal Mojari Co.
  {
    id: "40000000-0000-0000-0000-000000000011",
    shopId: SHOPS[7].id,
    categoryId: CATEGORIES[5].id,
    title: "Embroidered Velvet Wedding Mojari Shoes",
    slug: "embroidered-velvet-wedding-mojari",
    description: "Royal maroon velvet upper embellished with intricate zardozi wire embroidery. Built with double-cushioned genuine leather footbeds for all-day comfort.",
    tags: ["mojari", "juttis", "leather", "wedding", "embroidered", "footwear"],
    basePriceCents: 279900,
    comparePriceCents: 380000,
    isFeatured: false,
    ratingAvg: 4.83,
    ratingCount: 38,
    variants: [
      {
        sku: "RM-MOJ-MRN-08",
        title: "Maroon / Size UK 8",
        optionColor: "Royal Maroon",
        optionSize: "UK 8 (EU 42)",
        priceCents: 279900,
        stock: 18,
        imageUrl: "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=600&auto=format&fit=crop",
      },
      {
        sku: "RM-MOJ-MRN-09",
        title: "Maroon / Size UK 9",
        optionColor: "Royal Maroon",
        optionSize: "UK 9 (EU 43)",
        priceCents: 279900,
        stock: 24,
        imageUrl: "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=600&auto=format&fit=crop",
      },
      {
        sku: "RM-MOJ-MRN-10",
        title: "Maroon / Size UK 10",
        optionColor: "Royal Maroon",
        optionSize: "UK 10 (EU 44)",
        priceCents: 279900,
        stock: 16,
        imageUrl: "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=600&auto=format&fit=crop",
      },
    ],
  },
];

out(`-- 5. Products and Product Variants`);
for (const p of PRODUCTS) {
  out(
    `INSERT INTO products (id, shop_id, category_id, title, slug, description, tags, base_price_cents, compare_price_cents, is_featured, rating_avg, rating_count) VALUES (${esc(
      p.id
    )}, ${esc(p.shopId)}, ${esc(p.categoryId)}, ${esc(p.title)}, ${esc(p.slug)}, ${esc(
      p.description
    )}, ${escArray(p.tags)}, ${p.basePriceCents}, ${esc(
      p.comparePriceCents
    )}, ${p.isFeatured ? "TRUE" : "FALSE"}, ${p.ratingAvg}, ${p.ratingCount}) ON CONFLICT (shop_id, slug) DO NOTHING;`
  );

  for (const v of p.variants) {
    const varId = randomUUID();
    v.id = varId;
    out(
      `INSERT INTO product_variants (id, product_id, sku, title, option_color, option_size, price_cents, compare_price_cents, stock_quantity, image_url) VALUES (${esc(
        varId
      )}, ${esc(p.id)}, ${esc(v.sku)}, ${esc(v.title)}, ${esc(v.optionColor)}, ${esc(
        v.optionSize
      )}, ${v.priceCents}, ${esc(v.comparePriceCents)}, ${v.stock}, ${esc(
        v.imageUrl
      )}) ON CONFLICT (sku) DO NOTHING;`
    );

    out(
      `INSERT INTO inventory_logs (variant_id, delta_quantity, balance_after, reason, notes) VALUES (${esc(
        varId
      )}, ${v.stock}, ${v.stock}, 'initial', 'Initial inventory batch loaded') ON CONFLICT DO NOTHING;`
    );
  }
}
out(``);

// 6. Discount Coupons
out(`-- 6. Promo Coupons`);
out(
  `INSERT INTO coupons (code, description, discount_type, discount_value, min_order_cents, max_discount_cents, starts_at, expires_at, is_active) VALUES
  ('WELCOME10', 'Get 10% off on your first handcrafted order', 'percentage', 10, 100000, 50000, NOW() - INTERVAL '30 days', NOW() + INTERVAL '180 days', TRUE),
  ('FESTIVE20', 'Festive season special: 20% off on orders above ₹2,500', 'percentage', 20, 250000, 150000, NOW() - INTERVAL '10 days', NOW() + INTERVAL '90 days', TRUE),
  ('CRAFTLOOM15', 'Exclusive 15% discount on Craftloom Studio handloom textiles', 'percentage', 15, 150000, 80000, NOW() - INTERVAL '15 days', NOW() + INTERVAL '120 days', TRUE),
  ('FREESHIP', 'Free standard delivery across India on orders above ₹999', 'flat', 9900, 99900, 9900, NOW() - INTERVAL '60 days', NOW() + INTERVAL '365 days', TRUE)
  ON CONFLICT (code) DO NOTHING;`
);
out(``);

// 7. Ledger Accounts
out(`-- 7. Double-Entry Accounting Ledger Accounts`);
const ACC_PLATFORM_CASH = "50000000-0000-0000-0000-000000000001";
const ACC_PLATFORM_REVENUE = "50000000-0000-0000-0000-000000000002";
const ACC_SHOPPER_CLEARING = "50000000-0000-0000-0000-000000000003";

out(
  `INSERT INTO accounts (id, holder_type, holder_id, currency, balance_cents) VALUES
  (${esc(ACC_PLATFORM_CASH)}, 'platform', NULL, 'INR', 24850000),
  (${esc(ACC_PLATFORM_REVENUE)}, 'platform', NULL, 'INR', 4500000),
  (${esc(ACC_SHOPPER_CLEARING)}, 'shopper', NULL, 'INR', 0)
  ON CONFLICT ON CONSTRAINT uq_account_holder DO NOTHING;`
);

for (const shop of SHOPS) {
  out(
    `INSERT INTO accounts (holder_type, holder_id, currency, balance_cents) VALUES
    ('vendor', ${esc(shop.id)}, 'INR', 18500000)
    ON CONFLICT ON CONSTRAINT uq_account_holder DO NOTHING;`
  );
}
out(``);

// 8. Demo Multi-Vendor Orders for Shopper Priya Sharma
out(`-- 8. Multi-Vendor Split Orders & Shipments for Demo Shopper`);

const DEMO_ORDERS = [
  {
    orderId: "60000000-0000-0000-0000-000000000001",
    orderNumber: "BZ-2026-98124",
    totalCents: 849800,
    subtotalCents: 799800,
    taxCents: 39900,
    shippingCents: 0,
    discountCents: 0,
    paymentMethod: "mock_card",
    paymentStatus: "paid",
    status: "partially_shipped",
    shipments: [
      {
        shipmentId: "70000000-0000-0000-0000-000000000001",
        shipmentNumber: "BZ-2026-98124-S1",
        shopId: SHOPS[0].id, // Craftloom
        status: "shipped",
        courier: "Delhivery Surface & Express",
        trackingNumber: "DLHV83921045",
        subtotalCents: 499900,
        commissionCents: 49990,
        vendorPayoutCents: 449910,
        items: [
          {
            variantId: PRODUCTS[0].variants[0].id,
            productId: PRODUCTS[0].id,
            productTitle: PRODUCTS[0].title,
            variantTitle: PRODUCTS[0].variants[0].title,
            sku: PRODUCTS[0].variants[0].sku,
            unitPriceCents: 499900,
            quantity: 1,
            imageUrl: PRODUCTS[0].variants[0].imageUrl,
          },
        ],
        tracking: [
          { status: "placed", location: "Platform Order Center", msg: "Order placed and assigned to Craftloom Studio" },
          { status: "accepted", location: "Chanderi Weavers Hub", msg: "Craftloom Studio confirmed order and began packaging" },
          { status: "packed", location: "Craftloom Studio Warehouse", msg: "Quality inspection passed and sealed in tamper-proof box" },
          { status: "shipped", location: "Bhopal Sorting Hub", msg: "Picked up by Delhivery (DLHV83921045) and in transit to Bengaluru" },
        ],
      },
      {
        shipmentId: "70000000-0000-0000-0000-000000000002",
        shipmentNumber: "BZ-2026-98124-S2",
        shopId: SHOPS[3].id, // Brass & Bloom
        status: "packed",
        subtotalCents: 349900,
        commissionCents: 41988,
        vendorPayoutCents: 307912,
        items: [
          {
            variantId: PRODUCTS[5].variants[0].id,
            productId: PRODUCTS[5].id,
            productTitle: PRODUCTS[5].title,
            variantTitle: PRODUCTS[5].variants[0].title,
            sku: PRODUCTS[5].variants[0].sku,
            unitPriceCents: 349900,
            quantity: 1,
            imageUrl: PRODUCTS[5].variants[0].imageUrl,
          },
        ],
        tracking: [
          { status: "placed", location: "Platform Order Center", msg: "Order placed and assigned to Brass & Bloom" },
          { status: "accepted", location: "Moradabad Artisan Studio", msg: "Seller confirmed order and polished brass urli" },
          { status: "packed", location: "Moradabad Warehouse", msg: "Double foam wrapped and awaiting courier pickup" },
        ],
      },
    ],
  },
  {
    orderId: "60000000-0000-0000-0000-000000000002",
    orderNumber: "BZ-2026-74910",
    totalCents: 489800,
    subtotalCents: 489800,
    taxCents: 24400,
    shippingCents: 0,
    discountCents: 0,
    paymentMethod: "mock_upi",
    paymentStatus: "paid",
    status: "completed",
    shipments: [
      {
        shipmentId: "70000000-0000-0000-0000-000000000003",
        shipmentNumber: "BZ-2026-74910-S1",
        shopId: SHOPS[5].id, // Silver Moon Jewels
        status: "delivered",
        courier: "BlueDart Apex",
        trackingNumber: "BLDT99281744",
        subtotalCents: 389900,
        commissionCents: 58485,
        vendorPayoutCents: 331415,
        items: [
          {
            variantId: PRODUCTS[8].variants[0].id,
            productId: PRODUCTS[8].id,
            productTitle: PRODUCTS[8].title,
            variantTitle: PRODUCTS[8].variants[0].title,
            sku: PRODUCTS[8].variants[0].sku,
            unitPriceCents: 389900,
            quantity: 1,
            imageUrl: PRODUCTS[8].variants[0].imageUrl,
          },
        ],
        tracking: [
          { status: "placed", location: "Platform Center", msg: "Order placed and assigned" },
          { status: "shipped", location: "Jaipur Express Center", msg: "Handed over to BlueDart" },
          { status: "delivered", location: "Bengaluru, Karnataka", msg: "Delivered to Priya Sharma. OTP verified" },
        ],
      },
      {
        shipmentId: "70000000-0000-0000-0000-000000000004",
        shipmentNumber: "BZ-2026-74910-S2",
        shopId: SHOPS[4].id, // Spice Route
        status: "delivered",
        courier: "Delhivery Surface & Express",
        trackingNumber: "DLHV11029482",
        subtotalCents: 99900,
        commissionCents: 9990,
        vendorPayoutCents: 89910,
        items: [
          {
            variantId: PRODUCTS[6].variants[0].id,
            productId: PRODUCTS[6].id,
            productTitle: PRODUCTS[6].title,
            variantTitle: PRODUCTS[6].variants[0].title,
            sku: PRODUCTS[6].variants[0].sku,
            unitPriceCents: 99900,
            quantity: 1,
            imageUrl: PRODUCTS[6].variants[0].imageUrl,
          },
        ],
        tracking: [
          { status: "placed", location: "Platform Center", msg: "Order placed" },
          { status: "shipped", location: "Kochi Sorting Hub", msg: "In transit" },
          { status: "delivered", location: "Bengaluru, Karnataka", msg: "Package handed over to security desk" },
        ],
      },
    ],
  },
];

for (const ord of DEMO_ORDERS) {
  out(
    `INSERT INTO orders (id, order_number, user_id, status, total_cents, subtotal_cents, discount_cents, shipping_cents, tax_cents, shipping_address_json, billing_address_json, payment_method, payment_status, payment_reference) VALUES (${esc(
      ord.orderId
    )}, ${esc(ord.orderNumber)}, ${esc(USER_SHOPPER.id)}, ${esc(ord.status)}, ${ord.totalCents}, ${
      ord.subtotalCents
    }, ${ord.discountCents}, ${ord.shippingCents}, ${ord.taxCents}, ${escJson({
      recipientName: "Priya Sharma",
      phone: "+91 98765 43210",
      street: "Flat 402, Lotus Greens, Indiranagar",
      city: "Bengaluru",
      state: "Karnataka",
      postalCode: "560038",
      country: "India",
    })}, ${escJson({
      recipientName: "Priya Sharma",
      phone: "+91 98765 43210",
      street: "Flat 402, Lotus Greens, Indiranagar",
      city: "Bengaluru",
      state: "Karnataka",
      postalCode: "560038",
      country: "India",
    })}, ${esc(ord.paymentMethod)}, ${esc(ord.paymentStatus)}, ${esc(
      "PAY-MOCK-" + ord.orderNumber
    )}) ON CONFLICT (order_number) DO NOTHING;`
  );

  for (const s of ord.shipments) {
    out(
      `INSERT INTO shipments (id, order_id, shop_id, shipment_number, status, subtotal_cents, commission_cents, vendor_payout_cents, courier_name, tracking_number) VALUES (${esc(
        s.shipmentId
      )}, ${esc(ord.orderId)}, ${esc(s.shopId)}, ${esc(s.shipmentNumber)}, ${esc(
        s.status
      )}, ${s.subtotalCents}, ${s.commissionCents}, ${s.vendorPayoutCents}, ${esc(
        s.courier || null
      )}, ${esc(s.trackingNumber || null)}) ON CONFLICT (shipment_number) DO NOTHING;`
    );

    for (const item of s.items) {
      out(
        `INSERT INTO shipment_items (shipment_id, variant_id, product_id, product_title, variant_title, sku, unit_price_cents, quantity, total_price_cents, image_url) VALUES (${esc(
          s.shipmentId
        )}, ${esc(item.variantId)}, ${esc(item.productId)}, ${esc(item.productTitle)}, ${esc(
          item.variantTitle
        )}, ${esc(item.sku)}, ${item.unitPriceCents}, ${item.quantity}, ${
          item.unitPriceCents * item.quantity
        }, ${esc(item.imageUrl)});`
      );
    }

    if (s.tracking) {
      for (const tr of s.tracking) {
        out(
          `INSERT INTO shipment_tracking_events (shipment_id, status, location, message) VALUES (${esc(
            s.shipmentId
          )}, ${esc(tr.status)}, ${esc(tr.location)}, ${esc(tr.msg)});`
        );
      }
    }
  }
}
out(``);

// 9. Verified Customer Reviews
out(`-- 9. Verified Product Reviews`);
out(
  `INSERT INTO reviews (product_id, shop_id, user_id, rating, title, comment, verified_purchase) VALUES
  (${esc(PRODUCTS[0].id)}, ${esc(SHOPS[0].id)}, ${esc(USER_SHOPPER.id)}, 5, 'Exquisite Chanderi drape!', 'The gold zari is subtle, rich, and truly artisanal. Wore this to an intimate family function and received countless compliments.', TRUE),
  (${esc(PRODUCTS[8].id)}, ${esc(SHOPS[5].id)}, ${esc(USER_SHOPPER.id)}, 5, 'Sterling quality with beautiful patina', 'Lightweight on the ears yet makes an ornate statement. The seed pearls have a natural soft luster.', TRUE),
  (${esc(PRODUCTS[6].id)}, ${esc(SHOPS[4].id)}, ${esc(USER_SHOPPER.id)}, 5, 'Best Tellicherry pepper ever tasted', 'The aroma when cracked fresh is fruity and deeply complex. Elevates simple eggs and roasted potatoes completely.', TRUE)
  ON CONFLICT ON CONSTRAINT uq_review_product_user DO NOTHING;`
);
out(``);

// 10. Completed Settlement Batches for Vendor Aryan Gupta (Craftloom)
out(`-- 10. Vendor Settlement Batches`);
out(
  `INSERT INTO settlement_batches (shop_id, batch_number, status, gross_sales_cents, commission_cents, net_payout_cents, period_start, period_end, payout_reference, processed_at) VALUES
  (${esc(SHOPS[0].id)}, 'SET-2026-CL-001', 'processed', 1850000, 185000, 1665000, NOW() - INTERVAL '14 days', NOW() - INTERVAL '7 days', 'NEFT-HDFC-991204817', NOW() - INTERVAL '6 days'),
  (${esc(SHOPS[0].id)}, 'SET-2026-CL-002', 'processed', 2420000, 242000, 2178000, NOW() - INTERVAL '7 days', NOW(), 'NEFT-HDFC-991823901', NOW() - INTERVAL '1 day')
  ON CONFLICT (batch_number) DO NOTHING;`
);
out(``);

console.log(lines.join("\n"));
