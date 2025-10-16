# XML匯入功能設計文件

## 預期XML格式 (基於現有資料結構)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<bus_system>
  <routes>
    <route>
      <route_name>市民小巴8(測試線)</route_name>
      <direction>雙向</direction>
      <start_stop>花蓮轉運站</start_stop>
      <end_stop>東華大學</end_stop>
      <status>1</status>
      <stations>
        <station direction="去程">
          <stop_name>花蓮轉運站</stop_name>
          <latitude>23.9930200</latitude>
          <longitude>121.6032190</longitude>
          <stop_order>1</stop_order>
          <eta_from_start>0</eta_from_start>
          <address>花蓮縣花蓮市國聯一路98號</address>
        </station>
        <station direction="去程">
          <stop_name>中央路口</stop_name>
          <latitude>23.9925000</latitude>
          <longitude>121.6045000</longitude>
          <stop_order>2</stop_order>
          <eta_from_start>5</eta_from_start>
          <address>花蓮縣花蓮市中央路</address>
        </station>
        <station direction="回程">
          <stop_name>東華大學</stop_name>
          <latitude>23.9020000</latitude>
          <longitude>121.5450000</longitude>
          <stop_order>1</stop_order>
          <eta_from_start>0</eta_from_start>
          <address>花蓮縣壽豐鄉志學村大學路二段1號</address>
        </station>
      </stations>
    </route>
  </routes>
</bus_system>
```

## 功能特色

1. **智能重複檢查**: 整合現有的衝突檢查機制
2. **順序自動調整**: 利用已實作的三種處理模式
3. **批量處理**: 支援多路線同時匯入
4. **資料驗證**: 複用前端和後端的驗證邏輯
5. **錯誤處理**: 完善的錯誤回報和回滾機制

## API端點設計

- `POST /api/xml/upload` - XML檔案上傳
- `POST /api/xml/validate` - 驗證XML格式和資料
- `POST /api/xml/import` - 執行匯入操作
- `GET /api/xml/preview` - 預覽匯入結果

## 前端整合點

- 在RouteManagement.vue添加XML匯入按鈕
- 利用現有的模態框架構
- 複用站點衝突處理邏輯
- 整合現有的錯誤處理機制