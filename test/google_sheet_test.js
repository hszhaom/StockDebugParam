
function miany(){
  let strock_no="601899-bdl-1y-1";
  let sheel_code="data1y";
  stock_param=getSingleStockTemplateParam(strock_no);
  let multiplier_value=4;
  let danbian_value=0.85;
  let xiancang_value=0.24;
  let zhishu_value=0.88;
  let smoothing_value=0.08;
  let bordering_value=0.38;

  if(stock_param!=null && stock_param!="error"){
    multiplier_index=stock_param.multiplier_index==0?0:stock_param.multiplier_index+1;
    GetBDL(strock_no,sheel_code,multiplier_index);
  }else if(stock_param!="error"){
    stockcalDefalut(sheel_code,multiplier_value,danbian_value,xiancang_value,zhishu_value,smoothing_value,bordering_value);
    GetBDL(strock_no,sheel_code,0)
  }

}

function GetBDL(strock_no, sheel_code, index_z) {
    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    const sheet = spreadsheet.getSheetByName(sheel_code); // 或使用getActiveSheet()
    const multiplier = sheet.getRange("B6"); //XM 0.85
    const danbian = sheet.getRange("B7"); //单边保护	1.15
    const zlxc = sheet.getRange("B9"); //中立限仓
    const zhishu = sheet.getRange("B10"); //指跟
    const smoothing = sheet.getRange("B11"); //一窝蜂 smoothing	0.10
    const bordering = sheet.getRange("B12"); //一窝蜂 bordering	0.20

    //波动率调参1
    const xm_Arr = [3, 3.5, 4];
    const tp_Arr = [0.82, 0.83, 0.84, 0.85, 0.86, 0.87, 0.88, 0.89, 0.90, 0.91, 0.92];
    const zl_Arr = [0.3];
    const zg_Arr = [1];
    const ywfs_Arr = [0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1];
    const ywfb_Arr = [0.18, 0.19, 0.2, 0.21, 0.22, 0.23, 0.24, 0.25, 0.26, 0.27];

    var allCount = xm_Arr.length * tp_Arr.length * zl_Arr.length * zg_Arr.length * ywfs_Arr.length * ywfb_Arr.length;
    console.log('总共:' + allCount + '参数');
    for (let index = index_z; index < allCount; index++) {
        result_data = GetValue6(xm_Arr, tp_Arr, zl_Arr, zg_Arr, ywfs_Arr, ywfb_Arr, index);
        console.log('index:' + index + '--' + result_data);
      //xm赋值
        multiplier.setValue(result_data[0]);
        SpreadsheetApp.flush(); // 强制写入确保数据更新
        danbian.setValue(result_data[1]);
        SpreadsheetApp.flush(); // 强制写入确保数据更新
        zlxc.setValue(result_data[2]);
        SpreadsheetApp.flush(); // 强制写入确保数据更新
        zhishu.setValue(result_data[3]);
        SpreadsheetApp.flush(); // 强制写入确保数据更新
        smoothing.setValue(result_data[4]);
        SpreadsheetApp.flush(); // 强制写入确保数据更新
        bordering.setValue(result_data[5]);
        SpreadsheetApp.flush(); // 强制写入确保数据更新
        // 休眠10秒
        // 休眠10秒
        Utilities.sleep(generateRandomNumber() * 1000); // 10000毫秒 = 10秒[1,7](@ref)
        stockpush(sheel_code,strock_no,index,0,0,0,0,0);
    }
}

function GetValue6(xm_Arr, tp_Arr, zl_Arr, zg_Arr, ywfs_Arr, ywfb_Arr, index) {
    var tp_Count = tp_Arr.length * zl_Arr.length * zg_Arr.length * ywfs_Arr.length * ywfb_Arr.length;
    var zl_Count = zl_Arr.length * zg_Arr.length * ywfs_Arr.length * ywfb_Arr.length;
    var zg_Count = zg_Arr.length * ywfs_Arr.length * ywfb_Arr.length;
    var ywfs_Count = ywfs_Arr.length * ywfb_Arr.length;
    var ywfb_Count = ywfb_Arr.length;
    const xm_Index = parseInt(index / tp_Count);
    const tp_Index = parseInt((index % tp_Count) / zl_Count);
    const zl_Index = parseInt((index % zl_Count) / zg_Count);
    const zg_Index = parseInt((index % zg_Count) / ywfs_Count);
    const ywfs_Index = parseInt((index % ywfs_Count) / ywfb_Count);
    const ywfb_Index = index % ywfb_Count;
    return [xm_Arr[xm_Index], tp_Arr[tp_Index], zl_Arr[zl_Index], zg_Arr[zg_Index], ywfs_Arr[ywfs_Index], ywfb_Arr[ywfb_Index]];
}

function stockcalDefalut(sheel_code,multiplier_value,danbian_value,xiancang_value,zhishu_value,smoothing_value,bordering_value) {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = spreadsheet.getSheetByName(sheel_code); // 或使用getActiveSheet()
  const multiplier = sheet.getRange("B6"); //XM 0.85
  const danbian = sheet.getRange("B7"); //单边保护	1.15
  const xiancang = sheet.getRange("B9"); //中立限仓	0.25
  const zhishu = sheet.getRange("B10"); //指数跟踪	0.95
  const smoothing = sheet.getRange("B11"); //一窝蜂 smoothing	0.10
  const bordering = sheet.getRange("B12"); //一窝蜂 bordering	0.20

  multiplier.setValue(multiplier_value);
  SpreadsheetApp.flush(); // 强制写入确保数据更新[2](@ref)

  danbian.setValue(danbian_value);
  SpreadsheetApp.flush(); // 强制写入确保数据更新[2](@ref)

  xiancang.setValue(xiancang_value);
  SpreadsheetApp.flush(); // 强制写入确保数据更新[2](@ref)

  zhishu.setValue(zhishu_value);
  SpreadsheetApp.flush(); // 强制写入确保数据更新[2](@ref)

  smoothing.setValue(smoothing_value);
  SpreadsheetApp.flush(); // 强制写入确保数据更新[2](@ref)

  bordering.setValue(bordering_value);
  SpreadsheetApp.flush(); // 强制写入确保数据更新[2](@ref)

  Utilities.sleep(generateRandomNumber() * 1000); // 10000毫秒 = 10秒[1,7](@ref)
}

function stockpush(sheel_code,stock_no,multiplier_index,danbian_index,xiancang_index,zhishu_index,smoothing_index,bordering_index){
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = spreadsheet.getSheetByName(sheel_code); // 或使用getActiveSheet()

  const multiplier = sheet.getRange("B6").getValue().toFixed(2); //单边保护 0.85
  const danbian = sheet.getRange("B7").getValue().toFixed(2); //单边保护	1.15
  const jiancang = sheet.getRange("B9").getValue().toFixed(2); //中立限仓	0.25
  const zhishu = sheet.getRange("B10").getValue().toFixed(2); //指数跟踪	0.95
  const smoothing = sheet.getRange("B11").getValue().toFixed(2); //一窝蜂 smoothing	0.10
  const bordering = sheet.getRange("B12").getValue().toFixed(2); //一窝蜂 bordering	0.20


  const c_multiplier = sheet.getRange("I6").getValue().toFixed(2); //单边保护 0.85
  const c_danbian = sheet.getRange("I7").getValue().toFixed(2); //单边保护	1.15
  const c_jiancang = sheet.getRange("I9").getValue().toFixed(2); //中立限仓	0.25
  const c_zhishu = sheet.getRange("I10").getValue().toFixed(2); //指数跟踪	0.95
  const c_smoothing = sheet.getRange("I11").getValue().toFixed(2); //一窝蜂 smoothing	0.10
  const c_bordering = sheet.getRange("I12").getValue().toFixed(2); //一窝蜂 bordering	0.20

  if(multiplier!=c_multiplier || danbian!=c_danbian || jiancang!=c_jiancang || zhishu!=c_zhishu || smoothing!=c_smoothing || bordering!=c_bordering){
    Utilities.sleep(generateRandomNumber() * 1000); // 10000毫秒 = 10秒[1,7](@ref)
  }

  const return_rate = sheet.getRange("I15"); //回报率
  const annualized_rate = sheet.getRange("I16"); //年化回报率
  const maxdd = sheet.getRange("I17"); //Max DD
  const index_rate = sheet.getRange("I18"); //指数回报率
  const index_annualized_rate  = sheet.getRange("I19"); //指数年化回报率
  const max_index_dd = sheet.getRange("I20"); //指数 Max DD
  const fee_total = sheet.getRange("I21"); //指数回报率
  const fee_annualized = sheet.getRange("I22"); //费用总额
  const year_rate = sheet.getRange("I23"); //年换手率

  let paramload = {
    "stock_no": stock_no,
    "multiplier": multiplier,
    "danbian": danbian,
    "xiancang": jiancang,
    "zhishu": zhishu,
    "smoothing":smoothing,
    "bordering": bordering,
    "multiplier_index": multiplier_index,
    "danbian_index": danbian_index,
    "xiancang_index": xiancang_index,
    "zhishu_index": zhishu_index,
    "smoothing_index": smoothing_index,
    "bordering_index": bordering_index,
    "return_rate": return_rate.getValue().toFixed(4),
    "annualized_rate": annualized_rate.getValue().toFixed(4),
    "maxdd": maxdd.getValue().toFixed(4),
    "index_rate": index_rate.getValue().toFixed(4),
    "index_annualized_rate": index_annualized_rate.getValue().toFixed(4),
    "max_index_dd":max_index_dd.getValue().toFixed(4),
    "fee_total": fee_total.getValue().toFixed(4),
    "fee_annualized": fee_annualized.getValue().toFixed(4),
    "year_rate": year_rate.getValue().toFixed(4)
  };
  param_id=sendStockTemplateParamData(paramload);
}


function sendStockTemplateParamData(payload) {
  let url = 'http://sxapi.stplan.cn/api/Stock/InsertStockTemplateParam';

  let options = {
    'method': 'post',
    'contentType': 'application/json-patch+json',
    'payload': JSON.stringify(payload),
    'muteHttpExceptions': true
  };

  let response = UrlFetchApp.fetch(url, options);
  if (response.getResponseCode() == 200) {
    let responseData=response.getContentText();
    Logger.log('请求成功，响应内容：' +responseData);
    let parsedData = JSON.parse(responseData);
    return parsedData.ret_count;
  } else {
    Logger.log('请求失败，状态码：' + response.getResponseCode() + '，错误信息：' + response.getContentText());
    return 0;
  }
}


function getSingleStockTemplateParam(stock_no) {
  let url = 'http://sxapi.stplan.cn/api/Stock/GetSingleStockTemplateParam';
  let payload = {
    "stock_no": stock_no
  };

  let options = {
    'method': 'post',
    'contentType': 'application/json-patch+json',
    'payload': JSON.stringify(payload),
   'muteHttpExceptions': true
  };

  let response = UrlFetchApp.fetch(url, options);
  if (response.getResponseCode() == 200) {
    let responseContent = response.getContentText();
    try {
      let parsedData = JSON.parse(responseContent);
      // 这里可以根据实际返回结构进一步处理数据
      Logger.log(parsedData.ret_obj);
      return parsedData.ret_obj;
    } catch (e) {
      Logger.log('解析响应 JSON 数据时出错: '+ e);
      return "error";
    }
  } else {
    Logger.log('请求失败，状态码：' + response.getResponseCode() + '，错误信息：' + response.getContentText());
    return "error";
  }
}

function generateRandomNumber() {
 let randomNum = Math.floor(Math.random() * (30 - 20 + 1) + 20);
 return randomNum;
}
