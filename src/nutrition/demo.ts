import { estimateDishNutrition } from "./estimateDishNutrition";

const demos = [
  estimateDishNutrition("沙县鸭腿饭", {
    riceAmount: "normal",
    skinEaten: "full",
    sauceLevel: "normal",
  }),
  estimateDishNutrition("煎饼果子", {
    portionSize: "normal",
    crispyType: "crispy_cracker",
    sauceLevel: "normal",
  }),
  estimateDishNutrition("麻辣烫", {
    portionSize: "large",
    oilLevel: "high",
    sauceLevel: "high",
  }),
  estimateDishNutrition("黄焖鸡米饭", {
    riceAmount: "normal",
    sauceLevel: "normal",
    oilLevel: "normal",
  }),
  estimateDishNutrition("未知神秘盖饭"),
];

for (const result of demos) {
  console.log(JSON.stringify(result, null, 2));
}
