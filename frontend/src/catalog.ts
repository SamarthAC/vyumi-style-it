export type Category = "shirt" | "top" | "dress";
export interface Product {
  id: string;
  name: string;
  category: Category;
  cloth_type: string;
  description: string;
  image_filename: string;
  image_url?: string;
}

export const demoProducts: Product[] = [
  [
    "prod_shirt_classic_white",
    "Classic White Linen Shirt",
    "shirt",
    "Breathable linen. A timeless everyday essential.",
    "shirt_classic_white.png",
  ],
  [
    "prod_shirt_denim_blue",
    "Casual Denim Western Shirt",
    "shirt",
    "Easy denim with a little western character.",
    "shirt_denim_blue.png",
  ],
  [
    "prod_top_floral_summer",
    "Floral Summer Sleeveless Top",
    "top",
    "A fresh floral print for sun-filled days.",
    "top_floral_summer.png",
  ],
  [
    "prod_top_ribbed_knit",
    "Ribbed Knit Crewneck Top",
    "top",
    "Soft texture. A close fit. Effortlessly versatile.",
    "top_ribbed_knit.png",
  ],
  [
    "prod_dress_evening_velvet",
    "Emerald Evening Midi Dress",
    "dress",
    "Rich emerald and a silhouette made for evenings.",
    "dress_evening_velvet.png",
  ],
  [
    "prod_dress_summer_maxi",
    "Boho Floral Tiered Maxi Dress",
    "dress",
    "A flowing shape with an easy botanical print.",
    "dress_summer_maxi.png",
  ],
].map(([id, name, category, description, image_filename]) => ({
  id,
  name,
  category: category as Category,
  description,
  image_filename,
  cloth_type: category === "dress" ? "overall" : "upper",
  image_url: `/products/${id}/image`,
}));

export const palette: Record<
  string,
  { color: string; background: string; note: string }
> = {
  prod_shirt_classic_white: {
    color: "#eee9dd",
    background: "#eae8e0",
    note: "The everyday edit",
  },
  prod_shirt_denim_blue: {
    color: "#7593a6",
    background: "#e4e9ed",
    note: "Off-duty favorite",
  },
  prod_top_floral_summer: {
    color: "#ddaa97",
    background: "#eee5df",
    note: "A little sunshine",
  },
  prod_top_ribbed_knit: {
    color: "#8a9174",
    background: "#e7e9df",
    note: "Considered comfort",
  },
  prod_dress_evening_velvet: {
    color: "#376457",
    background: "#e1e7e1",
    note: "After-hours energy",
  },
  prod_dress_summer_maxi: {
    color: "#c39c76",
    background: "#eee5d9",
    note: "Slow summer days",
  },
};
